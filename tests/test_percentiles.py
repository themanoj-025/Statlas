"""Percentile computation tests — the formula is verified against
hand-calculated fractional ranks (methodology.md §5, percentile-rules.md §2).

Values [0.2, 0.4, 0.6, 0.8, 0.8] (N=5) give percentiles [0, 20, 40, 70, 70]:
  P = (B + 0.5*E) / N * 100   where B/E count PEERS (the player excluded)
  0.2 -> (0 + 0.5*0)/5*100 = 0
  0.4 -> (1 + 0.5*0)/5*100 = 20
  0.6 -> (2 + 0.5*0)/5*100 = 40
  0.8 -> (3 + 0.5*1)/5*100 = 70  (tied pair shares the midpoint of their block)
"""

from __future__ import annotations

from app.compute.percentiles import compute_percentiles, fractional_rank
from app.models import Player, StatSnapshot, Team
from tests.conftest import SNAPSHOT_DATE


def _seed_player(
    db,
    league,
    name,
    group,
    gls,
    dis=0.5,
    minutes=1000,
    xg=None,
    source="fbref",
    team_name="City",
):
    team = db.query(Team).filter_by(
        name=team_name, league_id=league.id
    ).first() or Team(name=team_name, league_id=league.id)
    db.add(team)
    db.flush()
    player = Player(canonical_name=name, position_group=group)
    db.add(player)
    db.flush()
    raw = {
        "si_gls_p90": gls,
        "si_dis_p90": dis,
        "si_cmp_pct": 80.0,
        "si_prgp_p90": 1.0,
        "si_prgc_p90": 1.0,
        "si_xag_p90": 0.1,
        "si_kp_p90": 0.5,
        "si_tkl_p90": 0.5,
        "si_int_p90": 0.5,
        "si_press_p90": 5.0,
        "si_sh_p90": 1.0,
        "si_xg_p90": xg if xg is not None else gls * 0.9,
        # pass-attempt sample-floor counter (what the FBref scraper writes) so
        # the cmp% display floor (>= 50 attempts) is met for every player.
        "_cmp_attempts": 300,
    }
    db.add(
        StatSnapshot(
            player_id=player.id,
            team_id=team.id,
            league_id=league.id,
            season="2025-26",
            scrape_date=SNAPSHOT_DATE,
            source=source,
            raw_stats=raw,
            minutes_played=minutes,
            matches_played=12,
            status="ingested",
        )
    )
    db.commit()
    return player


def test_fractional_rank_formula():
    values = [0.2, 0.4, 0.6, 0.8, 0.8]
    assert fractional_rank(0.2, values, invert=False) == 0.0
    assert fractional_rank(0.4, values, invert=False) == 20.0
    assert fractional_rank(0.6, values, invert=False) == 40.0
    assert fractional_rank(0.8, values, invert=False) == 70.0  # tied pair midpoint


def test_fractional_rank_inverted_for_lower_is_better():
    values = [0.2, 0.4, 0.6, 0.8, 0.8]  # dispossessed per 90 — lower is better
    assert fractional_rank(0.2, values, invert=True) == 80.0
    assert fractional_rank(0.4, values, invert=True) == 60.0
    assert fractional_rank(0.6, values, invert=True) == 40.0
    assert (
        fractional_rank(0.8, values, invert=True) == 10.0
    )  # tied pair shares midpoint


def test_percentiles_match_hand_calculated_values(db, premier_league, small_pool):
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.8)]:
        _seed_player(db, premier_league, name, "ST", gls)

    report = compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")
    assert report.percentile_rows == 5 * 12
    assert report.index_rows == 5
    assert report.cohorts == 1

    from app.models import PercentileSnapshot

    rows = (
        db.query(PercentileSnapshot, StatSnapshot, Player)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(PercentileSnapshot.metric_name == "si_gls_p90")
        .all()
    )
    by_player = {player.canonical_name: p.percentile_value for p, _, player in rows}
    assert by_player == {"A": 0.0, "B": 20.0, "C": 40.0, "D": 70.0, "E": 70.0}


def test_inverted_metric_percentiles(db, premier_league, small_pool):
    for name, dis in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.8)]:
        _seed_player(db, premier_league, name, "ST", gls=0.5, dis=dis)

    compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")

    from app.models import PercentileSnapshot, Player

    rows = (
        db.query(PercentileSnapshot, Player)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(PercentileSnapshot.metric_name == "si_dis_p90")
        .all()
    )
    by_player = {player.canonical_name: p.percentile_value for p, player in rows}
    assert by_player == {"A": 80.0, "B": 60.0, "C": 40.0, "D": 10.0, "E": 10.0}


def test_tier1_xg_precedence_uses_understat(db, premier_league, small_pool):
    """Tier-1 xG must come from Understat (one model per cohort), not FBref."""
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.8)]:
        _seed_player(db, premier_league, name, "ST", gls)
    # All five get Understat xG = 0.9 -> a fully-tied pool ranks at the block
    # midpoint: B=0, E=4 peers -> (0 + 0.5*4)/5*100 = 40 for every player
    # (the documented fractional-rank formula; a 5-way tie never reads 100).
    for name in ["A", "B", "C", "D", "E"]:
        player = db.query(Player).filter_by(canonical_name=name).one()
        team = db.query(Team).filter_by(league_id=premier_league.id).first()
        db.add(
            StatSnapshot(
                player_id=player.id,
                team_id=team.id,
                league_id=premier_league.id,
                season="2025-26",
                scrape_date=SNAPSHOT_DATE,
                source="understat",
                raw_stats={
                    "si_xg_p90": 0.9,
                    "si_sh_p90": 2.0,
                    "si_xag_p90": 0.3,
                    "si_kp_p90": 1.0,
                },
                minutes_played=1000,
                matches_played=12,
                status="ingested",
            )
        )
    db.commit()

    compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")

    from app.models import PercentileSnapshot

    rows = (
        db.query(PercentileSnapshot, Player)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(PercentileSnapshot.metric_name == "si_xg_p90")
        .all()
    )
    assert len(rows) == 5
    assert {p.percentile_value for p, _ in rows} == {40.0}


def test_pool_below_minimum_is_skipped(db, premier_league, small_pool):
    for name, gls in [("A", 0.2), ("B", 0.4)]:  # N=2 < min pool (5)
        _seed_player(db, premier_league, name, "ST", gls)
    report = compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")
    assert report.percentile_rows == 0
    assert any("si_gls_p90" in item for item in report.skipped_small_pool)


def test_below_threshold_players_are_excluded(db, premier_league, small_pool):
    for name, gls in [("A", 0.2), ("B", 0.4), ("C", 0.6), ("D", 0.8), ("E", 0.8)]:
        _seed_player(db, premier_league, name, "ST", gls)
    # 'F' has only 480 minutes — must not enter any pool.
    _seed_player(db, premier_league, "F", "ST", gls=9.0, minutes=480)

    compute_percentiles(db, snapshot_date=SNAPSHOT_DATE, season="2025-26")

    from app.models import PercentileSnapshot, Player

    rows = (
        db.query(PercentileSnapshot, Player)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .all()
    )
    assert "F" not in {player.canonical_name for _, player in rows}
