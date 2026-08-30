"""Closeout C1 — tier-completeness gate + cross-tier transfer regression.

Two scenarios the Phase 1 fixture tests could not cover:

1. **Same-season cross-tier transfer.** A player with qualifying snapshots in
   TWO leagues of DIFFERENT tiers (e.g. moved from the Premier League to the
   Championship mid-season) previously collided on the percentile unique key
   (stat_snapshot_id, metric_name): the job keyed source precedence by
   (player, source) with no tier dimension, so both tiers' cohorts resolved
   the same snapshot and the second insert raised a unique-key violation
   ("fails loudly today" — the documented deviation). After the fix the key is
   (stat_snapshot_id, metric_name, league_tier) and each tier resolves the
   player's own-tier snapshot.

2. **Tier-completeness gate (§1.4).** Percentiles for a tier are only computed
   when EVERY league in that tier is ingested for the season (coverage matrix
   as arbiter). With require_tier_completeness=True, a tier with a missing
   league is withheld entirely — no partially-populated pool is ever ranked.
"""

from __future__ import annotations

from app.config import load_tiers
from app.models import DataCoverage, League, Player, StatSnapshot, Team
from tests.conftest import SNAPSHOT_DATE


def _seed_league(db, slug, name, country, tier) -> League:
    league = League(slug=slug, name=name, country=country, tier=tier, external_ids={})
    db.add(league)
    db.flush()
    return league


def _seed_player(
    db, league, team_name, name, group, gls, minutes=1000
) -> tuple[Player, Team]:
    team = db.query(Team).filter_by(name=team_name, league_id=league.id).first()
    if team is None:
        team = Team(name=team_name, league_id=league.id, external_ids={})
        db.add(team)
        db.flush()
    player = Player(canonical_name=name, position_group=group)
    db.add(player)
    db.flush()
    raw = {
        "si_gls_p90": gls,
        "si_dis_p90": 0.5,
        "si_cmp_pct": 80.0,
        "si_prgp_p90": 1.0,
        "si_prgc_p90": 1.0,
        "si_xag_p90": 0.1,
        "si_kp_p90": 0.5,
        "si_tkl_p90": 0.5,
        "si_int_p90": 0.5,
        "si_press_p90": 5.0,
        "si_sh_p90": 1.0,
        "si_xg_p90": gls * 0.9,
        "_cmp_attempts": 300,
    }
    db.add(
        StatSnapshot(
            player_id=player.id,
            team_id=team.id,
            league_id=league.id,
            season="2025-26",
            scrape_date=SNAPSHOT_DATE,
            source="fbref",
            raw_stats=raw,
            minutes_played=minutes,
            matches_played=12,
            status="ingested",
        )
    )
    db.commit()
    return player, team


def _cover_league(db, league: League, season: str = "2025-26") -> None:
    db.add(
        DataCoverage(
            league_id=league.id,
            source="fbref",
            source_identifier=league.slug,
            seasons_available=[season],
            last_successful_scrape=SNAPSHOT_DATE,
            status="active",
        )
    )
    db.commit()


def _seed_st_cohort(db, league: League, prefix: str, n: int = 5) -> list[Player]:
    players = []
    for i in range(n):
        p, _ = _seed_player(
            db, league, f"{prefix} FC", f"{prefix} Player {i}", "ST", gls=0.2 + 0.15 * i
        )
        players.append(p)
    return players


def test_cross_tier_transfer_same_season_no_collision(db, small_pool) -> None:
    """A player with qualifying snapshots in two tiers the same season must get
    percentile rows for BOTH tiers without a unique-key collision, each row
    attached to its own tier's snapshot."""
    from app.compute.percentiles import compute_percentiles
    from app.models import PercentileSnapshot

    t1 = _seed_league(db, "premier-league", "Premier League", "England", "tier_1")
    t2 = _seed_league(db, "championship", "Championship", "England", "tier_3")

    _seed_st_cohort(db, t1, "PL", n=4)
    _seed_st_cohort(db, t2, "CH", n=4)

    # The transfer player: two snapshots, one per tier, same season/date.
    transfer, _ = _seed_player(db, t1, "PL FC", "Transfer Star", "ST", gls=0.9)
    t2_snapshot = None
    team2 = db.query(Team).filter_by(name="CH FC", league_id=t2.id).first()
    transfer_player = db.get(Player, transfer.id)
    raw = {
        "si_gls_p90": 0.9,
        "si_dis_p90": 0.5,
        "si_cmp_pct": 80.0,
        "si_prgp_p90": 1.0,
        "si_prgc_p90": 1.0,
        "si_xag_p90": 0.1,
        "si_kp_p90": 0.5,
        "si_tkl_p90": 0.5,
        "si_int_p90": 0.5,
        "si_press_p90": 5.0,
        "si_sh_p90": 1.0,
        "si_xg_p90": 0.81,
        "_cmp_attempts": 300,
    }
    db.add(
        StatSnapshot(
            player_id=transfer_player.id,
            team_id=team2.id,
            league_id=t2.id,
            season="2025-26",
            scrape_date=SNAPSHOT_DATE,
            source="fbref",
            raw_stats=raw,
            minutes_played=1000,
            matches_played=12,
            status="ingested",
        )
    )
    db.commit()
    t2_snapshot = (
        db.query(StatSnapshot)
        .filter(
            StatSnapshot.player_id == transfer_player.id,
            StatSnapshot.league_id == t2.id,
        )
        .one()
    )

    # Previously this raised an IntegrityError (unique key collision) or
    # silently attached both tiers to the same snapshot. Now: 5 players per
    # tier (4 cohort + transfer), tiers computed independently.
    report = compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")

    assert report.cohorts == 2  # tier_1/ST + tier_3/ST
    assert report.percentile_rows == 2 * 5 * 12  # 5 players x 12 metrics x 2 tiers

    # The transfer player's tier_3 rows attach to the tier_3 snapshot, and the
    # tier_1 rows to the tier_1 snapshot — never one snapshot for both tiers.
    rows = (
        db.query(PercentileSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(StatSnapshot.player_id == transfer_player.id)
        .all()
    )
    assert rows, "transfer player must have percentile rows"
    tiers_covered = {r.league_tier for r in rows}
    assert tiers_covered == {"tier_1", "tier_3"}
    tier3_rows = [r for r in rows if r.league_tier == "tier_3"]
    assert all(r.stat_snapshot_id == t2_snapshot.id for r in tier3_rows)


def test_tier_completeness_gate_withholds_incomplete_tier(db, small_pool) -> None:
    """§1.4 gate: when require_tier_completeness=True, a tier missing ANY of its
    leagues is withheld entirely — no partially-populated pool is ranked."""
    from app.compute.percentiles import compute_percentiles

    t1 = _seed_league(db, "premier-league", "Premier League", "England", "tier_1")
    _seed_st_cohort(db, t1, "PL", n=5)
    _cover_league(db, t1)

    # Tier 1 has 5 leagues in tiers.json; only premier-league is covered -> gate
    # must withhold the WHOLE tier even though a qualifying pool exists.
    report = compute_percentiles(
        db,
        snapshot_date=SNAPSHOT_DATE,
        season="2025-26",
        require_tier_completeness=True,
    )
    assert report.percentile_rows == 0
    assert any("tier_1" in item for item in report.skipped_incomplete_tiers)


def test_tier_completeness_gate_passes_when_tier_complete(db, small_pool) -> None:
    """When every league in the tier is covered, the gate lets the tier through."""
    from app.compute.percentiles import compute_percentiles

    # Build a synthetic single-league tier by checking tiers.json membership.
    tiers = load_tiers()
    # Use tier_3 (5 leagues) but cover them ALL — build players in one league
    # and coverage rows for every tier_3 league.
    t3_leagues = [
        slug for slug, cfg in tiers["leagues"].items() if cfg["tier"] == "tier_3"
    ]
    assert len(t3_leagues) >= 5
    main = None
    for slug in t3_leagues:
        league = _seed_league(db, slug, slug, "Country", "tier_3")
        if main is None:
            main = league
        _cover_league(db, league)
    _seed_st_cohort(db, main, "T3", n=5)

    report = compute_percentiles(
        db,
        snapshot_date=SNAPSHOT_DATE,
        season="2025-26",
        require_tier_completeness=True,
    )
    assert report.percentile_rows == 5 * 12
    # tier_3 (fully covered) is NOT withheld; tier_1/tier_2 have no coverage in
    # this test, so they ARE withheld — that is the gate working.
    assert "tier_3" not in report.skipped_incomplete_tiers


def test_gate_off_by_default_preserves_prior_behavior(db, small_pool) -> None:
    """require_tier_completeness defaults to False — existing single-league
    integration contracts keep working (documented in weekly_refresh)."""
    from app.compute.percentiles import compute_percentiles

    t1 = _seed_league(db, "premier-league", "Premier League", "England", "tier_1")
    _seed_st_cohort(db, t1, "PL", n=5)
    _cover_league(db, t1)

    report = compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")
    assert report.percentile_rows == 5 * 12
    assert report.skipped_incomplete_tiers == []
