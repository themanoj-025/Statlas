"""End-to-end integration test: the full weekly refresh against fixture-backed
source fakes, asserting the database ends in the expected state and that the
internal query layer serves only published rows.

The sources are FAKES returning RawPlayerStatRecord lists (the HTML/JSON
parsers are unit-tested separately against their own fixtures). This proves the
orchestration sequence, idempotent storage, reconciliation, anomaly gating,
percentile/index computation, publishing, and queries all work together.
"""

from __future__ import annotations

from app.models import League, PercentileSnapshot, Player, PlayerNameAlias, StatSnapshot
from app.orchestration.weekly_refresh import run_weekly_refresh
from app.queries.coverage_queries import get_data_coverage
from app.queries.leaderboard_queries import get_leaderboard
from app.queries.player_queries import get_player_percentiles, get_player_profile
from app.sources.base import RawPlayerStatRecord
from tests.conftest import SNAPSHOT_DATE

SEASON = "2025-26"


def _st_raw(gls, xg, sh, prgp, prgc, xag, kp, tkl, int_, press, cmp, dis) -> dict[str, object]:
    return {
        "si_gls_p90": gls,
        "si_xg_p90": xg,
        "si_sh_p90": sh,
        "si_prgp_p90": prgp,
        "si_prgc_p90": prgc,
        "si_xag_p90": xag,
        "si_kp_p90": kp,
        "si_tkl_p90": tkl,
        "si_int_p90": int_,
        "si_press_p90": press,
        "si_cmp_pct": cmp,
        "si_dis_p90": dis,
        # pass-attempt sample-floor counter (what the FBref scraper writes) so
        # the cmp% display floor (>= 50 attempts) is met for every player.
        "_cmp_attempts": 300,
    }


def _st_record(name, ext_id, team, minutes, gls, xg, dis=0.5):
    return RawPlayerStatRecord(
        source="fbref",
        season=SEASON,
        league_slug="premier-league",
        player_name=name,
        team_name=team,
        minutes_played=minutes,
        matches_played=30,
        position_group="ST",
        position_code="FW",
        raw_stats=_st_raw(gls, xg, gls, 1.0, 1.0, 0.1, 0.5, 0.5, 0.5, 5.0, 80.0, dis),
        external_ids={"fbref": ext_id},
    )


def _understat_record(name, understat_id, team, xg):
    return RawPlayerStatRecord(
        source="understat",
        season=SEASON,
        league_slug="premier-league",
        player_name=name,
        team_name=team,
        minutes_played=1000,
        matches_played=30,
        position_group=None,
        raw_stats={"si_xg_p90": xg, "si_sh_p90": 2.0},
        external_ids={"understat": understat_id},
    )


class FakeFBrefSource:
    source_name = "fbref"

    def __init__(self, records):
        self.records = records

    def fetch_league_stats(self, league_slug, season) -> list[object]:
        return [
            r
            for r in self.records
            if r.league_slug == league_slug and r.season == season
        ]

    def get_rate_limit_seconds(self) -> int:
        return 10.0


class FakeUnderstatSource:
    source_name = "understat"

    def __init__(self, records):
        self.records = records

    def fetch_league_stats(self, league_slug, season) -> list[object]:
        return [
            r
            for r in self.records
            if r.league_slug == league_slug and r.season == season
        ]

    def get_rate_limit_seconds(self) -> int:
        return 5.0


def _fixtures() -> tuple[object, ...]:
    fbref = [
        _st_record("Player A", "aaaaaaaa", "Manchester City", 1000, 0.2, 0.3),
        _st_record("Player B", "bbbbbbbb", "Manchester City", 1100, 0.4, 0.4),
        _st_record("Player C", "cccccccc", "Liverpool", 1200, 0.6, 0.6),
        _st_record("Player D", "dddddddd", "Liverpool", 1300, 0.8, 0.8),
        _st_record("Player E", "eeeeeeee", "Arsenal", 1400, 0.8, 0.8),
    ]
    understat = [
        _understat_record("Player A", 9001, "Manchester City", 0.9),
        _understat_record("Player E", 9005, "Arsenal", 0.9),
    ]
    return fbref, understat


def test_full_weekly_refresh_end_to_end(db, small_pool) -> None:
    fbref, understat = _fixtures()
    report = run_weekly_refresh(
        db,
        SEASON,
        snapshot_date=SNAPSHOT_DATE,
        league_slugs=["premier-league"],
        fbref_source=FakeFBrefSource(fbref),
        understat_source=FakeUnderstatSource(understat),
    )

    # -- orchestration report -----------------------------------------------
    assert report.errors == []
    assert report.snapshots_inserted == 7  # 5 fbref + 2 understat
    assert report.records_unmatched == 0
    assert report.anomalies_bounds == 0
    assert report.percentile_rows == 5 * 12  # 5 ST players x 12 metrics
    assert report.index_rows == 5
    assert report.published_rows == 65  # metric rows + index rows, all published

    # -- database state ------------------------------------------------------
    assert db.query(League).filter_by(slug="premier-league").count() == 1
    assert db.query(Player).count() == 5  # understat records merged, no duplicates
    assert db.query(StatSnapshot).count() == 7
    assert db.query(PercentileSnapshot).filter_by(is_published=True).count() == 65

    # understat aliases written by reconciliation (name+team match)
    assert db.query(PlayerNameAlias).filter_by(source="understat").count() == 2

    # coverage rows written for both sources
    coverage = {c["source"] for c in get_data_coverage(db)}
    assert coverage == {"fbref", "understat"}
    from app.queries.coverage_queries import has_source_coverage

    assert has_source_coverage(
        db, source="fbref", source_identifier="premier-league", season=SEASON
    )
    assert not has_source_coverage(
        db, source="statsbomb", source_identifier="anything", season=SEASON
    )

    # -- query layer (published only) -----------------------------------------
    players = {p.canonical_name: p.id for p in db.query(Player).all()}
    profile = get_player_profile(db, players["Player A"])
    assert profile["position_group"] == "ST"
    assert profile["current_team"] == "Manchester City"

    percentiles = get_player_percentiles(db, players["Player A"])
    assert percentiles is not None
    assert len(percentiles["percentiles"]) == 12
    assert percentiles["index"] is not None

    leaderboard = get_leaderboard(
        db,
        league_slug="premier-league",
        position_group="ST",
        metric="si_index",
        season=SEASON,
        limit=50,
    )
    assert len(leaderboard) == 5
    values = [e["value"] for e in leaderboard]
    assert values == sorted(values, reverse=True)

    # Player E (gls 0.8 + understat xG 0.9, both top of their pools) tops the
    # board; Player B (gls 0.4, xG 0.4 — bottom of every metric pool) is last.
    # Note A's understat xG boost (0.9 vs B's 0.4) lifts A above B/C/D on the
    # index despite the lowest goals percentile.
    assert leaderboard[0]["name"] == "Player E"
    assert leaderboard[-1]["name"] == "Player B"


def test_blocked_player_is_excluded_from_pools(db, small_pool) -> None:
    fbref, understat = _fixtures()
    run_weekly_refresh(
        db,
        SEASON,
        snapshot_date=SNAPSHOT_DATE,
        league_slugs=["premier-league"],
        fbref_source=FakeFBrefSource(fbref),
        understat_source=FakeUnderstatSource(understat),
    )

    # simulate an unresolved anomaly on Player A's fbref snapshot
    from app.models import IngestionAnomaly

    snap_a = (
        db.query(StatSnapshot)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(Player.canonical_name == "Player A", StatSnapshot.source == "fbref")
        .one()
    )
    db.add(
        IngestionAnomaly(
            stat_snapshot_id=snap_a.id,
            field_name="si_gls_p90",
            raw_value="99.0",
            expected_range="0..5",
            resolved=False,
        )
    )
    db.commit()

    # new scrape date so percentiles are recomputed from the flagged data
    from datetime import timedelta

    later = SNAPSHOT_DATE + timedelta(days=7)
    report = run_weekly_refresh(
        db,
        SEASON,
        snapshot_date=later,
        league_slugs=["premier-league"],
        fbref_source=FakeFBrefSource(fbref),
        understat_source=FakeUnderstatSource(understat),
    )
    assert report.blocked_players == 1
    # Player A is blocked, dropping the Tier-1 ST pool to 4 players — below the
    # minimum pool size (5 in the test override) — so the later run publishes
    # NO percentile rows at all (min-pool rule: a pool below the minimum is
    # never ranked). A is therefore neither ranked nor rankable: no rows are
    # written against any 'later' snapshot.
    from app.models import PercentileSnapshot

    later_snap_ids = {
        s.id for s in db.query(StatSnapshot).filter(StatSnapshot.scrape_date == later)
    }
    assert later_snap_ids
    assert (
        db.query(PercentileSnapshot)
        .filter(PercentileSnapshot.stat_snapshot_id.in_(later_snap_ids))
        .count()
        == 0
    )
