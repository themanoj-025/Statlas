"""Anomaly detection tests (Constitution §3: flagged values are never silently
published)."""

from __future__ import annotations

from app.compute.anomaly_check import (
    blocked_player_ids,
    check_snapshot_bounds,
    cross_source_spot_check,
    resolve_anomaly,
)
from app.models import IngestionAnomaly, Player, StatSnapshot, Team
from tests.conftest import SNAPSHOT_DATE


def _snapshot(db, name, raw, source="fbref", minutes=1000, league=None):
    from app.models import League

    league = league or db.query(League).first()
    team = db.query(Team).filter_by(name=f"{name} FC", league_id=league.id).first()
    if team is None:
        team = Team(name=f"{name} FC", league_id=league.id)
        db.add(team)
    player = db.query(Player).filter_by(canonical_name=name).first()
    if player is None:
        player = Player(canonical_name=name, position_group="ST")
        db.add(player)
    db.flush()
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id,
        league_id=league.id,
        season="2025-26",
        scrape_date=SNAPSHOT_DATE,
        source=source,
        raw_stats=raw,
        minutes_played=minutes,
        matches_played=12,
    )
    db.add(snap)
    db.commit()
    return snap


def test_impossible_value_is_flagged(db, premier_league):
    snap = _snapshot(db, "A", {"si_gls_p90": 99.0}, league=premier_league)
    flagged = check_snapshot_bounds(db, snapshot_date=SNAPSHOT_DATE)
    assert flagged == 1
    assert snap.status == "flagged"
    anomaly = db.query(IngestionAnomaly).one()
    assert anomaly.field_name == "si_gls_p90"
    assert anomaly.raw_value == "99.0"
    assert anomaly.expected_range == "0.0..5.0"
    assert anomaly.resolved is False

    assert blocked_player_ids(db, snapshot_date=SNAPSHOT_DATE) == {snap.player_id}


def test_minutes_and_matches_bounds(db, premier_league):
    _snapshot(db, "A", {"si_gls_p90": 0.3}, minutes=-5, league=premier_league)
    flagged = check_snapshot_bounds(db, snapshot_date=SNAPSHOT_DATE)
    assert flagged == 1
    anomaly = db.query(IngestionAnomaly).one()
    assert anomaly.field_name == "minutes_played"


def test_undocumented_metric_is_an_anomaly(db, premier_league):
    _snapshot(db, "A", {"si_gls_p90": 0.3, "magic_score": 9000}, league=premier_league)
    assert check_snapshot_bounds(db, snapshot_date=SNAPSHOT_DATE) == 1
    assert db.query(IngestionAnomaly).one().field_name == "magic_score"


def test_empty_fbref_extraction_is_flagged(db, premier_league):
    """A played fbref snapshot with zero extracted registry metrics is a
    schema-drift red flag (silent rename would otherwise pass unnoticed)."""
    _snapshot(db, "A", {}, source="fbref", league=premier_league)
    flagged = check_snapshot_bounds(db, snapshot_date=SNAPSHOT_DATE)
    assert flagged == 1
    anomaly = db.query(IngestionAnomaly).one()
    assert anomaly.field_name == "raw_stats"
    assert anomaly.raw_value == "<empty>"
    player_a = db.query(Player).filter_by(canonical_name="A").one()
    assert blocked_player_ids(db, snapshot_date=SNAPSHOT_DATE) == {player_a.id}


def test_resolution_unblocks_player(db, premier_league):
    snap = _snapshot(db, "A", {"si_gls_p90": 99.0}, league=premier_league)
    check_snapshot_bounds(db, snapshot_date=SNAPSHOT_DATE)
    assert blocked_player_ids(db, snapshot_date=SNAPSHOT_DATE) == {snap.player_id}

    anomaly = db.query(IngestionAnomaly).one()
    resolve_anomaly(db, anomaly.id, note="verified against match report")
    assert blocked_player_ids(db, snapshot_date=SNAPSHOT_DATE) == set()


def test_cross_source_divergence_is_flagged(db, premier_league):
    fbref = _snapshot(
        db,
        "A",
        {"si_xg_p90": 0.5, "si_sh_p90": 1.0},
        source="fbref",
        league=premier_league,
    )
    _snapshot(
        db,
        "A",
        {"si_xg_p90": 3.0, "si_sh_p90": 6.0},
        source="understat",
        league=premier_league,
    )
    flagged = cross_source_spot_check(db, snapshot_date=SNAPSHOT_DATE, sample_size=100)
    # both overlapping metrics (xG 0.5 vs 3.0, shots 1.0 vs 6.0) diverge -> 2 flags
    assert flagged == 2
    anomalies = (
        db.query(IngestionAnomaly)
        .filter(IngestionAnomaly.field_name.like("cross_source:%"))
        .all()
    )
    assert len(anomalies) == 2
    assert all(
        a.stat_snapshot_id is None for a in anomalies
    )  # relationship flag, not a row flag
    xg_flag = next(a for a in anomalies if a.field_name == "cross_source:si_xg_p90")
    assert "fbref=0.5" in xg_flag.raw_value

    # the divergence itself does not block the player; only value-bounds do
    assert fbref.player_id not in blocked_player_ids(db, snapshot_date=SNAPSHOT_DATE)
