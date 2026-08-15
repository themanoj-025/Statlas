"""Trend / time-series query tests (Phase 3 — Part A).

The deliberately constructed gap case (a player missing one scrape date while
their league calendar has it) is the quality-gate test: the trend must mark
the break (`gap_after` + a `gaps` span) — never interpolate through it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models import League, PercentileSnapshot, Player, StatSnapshot, Team

SEASON = "2025-26"
T0 = datetime(2026, 7, 1, 3, 0, 0, tzinfo=timezone.utc)


def _snap(db, player, team, date, raw, minutes=1000, status="ingested"):
    snap = StatSnapshot(
        player_id=player.id,
        team_id=team.id,
        league_id=player.league_id,
        season=SEASON,
        scrape_date=date,
        source="fbref",
        raw_stats=raw,
        minutes_played=minutes,
        matches_played=30,
        status=status,
    )
    db.add(snap)
    db.flush()
    return snap


@pytest.fixture()
def trend_env(db):
    """A league + two teams + two players, then helper builders."""
    league = League(
        slug="premier-league", name="Premier League", country="England", tier="tier_1"
    )
    db.add(league)
    db.flush()
    t_a = Team(name="Manchester City", league_id=league.id, external_ids={})
    t_b = Team(name="Liverpool", league_id=league.id, external_ids={})
    db.add_all([t_a, t_b])
    db.flush()
    p_a = Player(
        canonical_name="Player A",
        position_group="ST",
        current_team_id=t_a.id,
        external_ids={"fbref": "a"},
    )
    p_b = Player(
        canonical_name="Player B",
        position_group="ST",
        current_team_id=t_b.id,
        external_ids={"fbref": "b"},
    )
    db.add_all([p_a, p_b])
    db.commit()
    p_a.league_id = league.id  # convenience for the snapshot helper
    p_b.league_id = league.id
    return {"db": db, "league": league, "t_a": t_a, "t_b": t_b, "p_a": p_a, "p_b": p_b}


def _seed_history(env, dates, player, team, base=0.5, drift=0.0):
    """One snapshot per date for `player`, with the metric drifting by `drift`
    per step so ordering assertions are exact."""
    db = env["db"]
    for i, date in enumerate(dates):
        _snap(db, player, team, date, {"si_gls_p90": round(base + drift * i, 4)})
    db.commit()


def test_gap_is_flagged_not_interpolated(trend_env):
    """Quality gate Part D: a deliberately missing snapshot produces an
    explicit break (gap_after + gaps span), never a false smooth line."""
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    dates = [T0 + timedelta(days=7 * i) for i in range(6)]
    # League calendar: 6 dates (Player B has ALL of them). The gap player is
    # missing date index 3 — the calendar still carries it via Player B.
    for i, date in enumerate(dates):
        _snap(db, env["p_b"], env["t_b"], date, {"si_gls_p90": 0.3})
        if i == 3:
            continue
        _snap(db, player, team, date, {"si_gls_p90": 0.5 + 0.1 * i})
    db.commit()

    from app.queries.trend_queries import get_player_trend

    trend = get_player_trend(db, player.id, "si_gls_p90", window=10)
    assert trend["available"] == 5
    assert trend["insufficient"] is False
    assert trend["granularity"] == "snapshot"  # honest: never per-match precision

    points = trend["points"]
    # The point before the missing date carries the break marker.
    flagged = [p for p in points if p["gap_after"]]
    assert len(flagged) == 1
    assert flagged[0]["date"].startswith("2026-07-15")  # the date before the gap
    assert trend["gaps"] == [
        {
            "from_date": flagged[0]["date"],
            "to_date": points[3]["date"],  # the next snapshot AFTER the gap
            "missed_dates": ["2026-07-22T03:00:00"],
        }
    ]
    # Values are the real snapshots on both sides — nothing invented between.
    assert points[3]["raw"] == 0.9
    assert points[4]["raw"] == 1.0


def test_rolling_window_keeps_last_n(trend_env):
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    dates = [T0 + timedelta(days=7 * i) for i in range(8)]
    _seed_history(env, dates, player, team, base=0.2, drift=0.1)

    from app.queries.trend_queries import get_player_trend

    trend = get_player_trend(db, player.id, "si_gls_p90", window=5)
    assert trend["available"] == 5
    # Oldest 3 dates dropped; the first kept date is index 3 (07-22), the
    # last is index 7 (07-01 + 49 days = 08-19).
    assert trend["points"][0]["date"].startswith("2026-07-22")
    assert trend["points"][-1]["date"].startswith("2026-08-19")

    full = get_player_trend(db, player.id, "si_gls_p90", window=10)
    assert full["available"] == 8


def test_insufficient_history_is_honest(trend_env):
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    dates = [T0 + timedelta(days=7 * i) for i in range(3)]
    _seed_history(env, dates, player, team)

    from app.queries.trend_queries import MIN_TREND_SNAPSHOTS, get_player_trend

    trend = get_player_trend(db, player.id, "si_gls_p90", window=5)
    assert trend["available"] == 3
    assert trend["min_snapshots"] == MIN_TREND_SNAPSHOTS == 5
    assert trend["insufficient"] is True  # UI copy: "3 of 5 minimum snapshots"


def test_transfer_annotation_derived_from_team_change(trend_env):
    env = trend_env
    db = env["db"]
    dates = [T0 + timedelta(days=7 * i) for i in range(4)]
    for i, date in enumerate(dates):
        team = env["t_a"] if i < 2 else env["t_b"]
        _snap(db, env["p_a"], team, date, {"si_gls_p90": 0.4 + 0.05 * i})
    db.commit()

    from app.queries.trend_queries import get_player_trend

    trend = get_player_trend(db, env["p_a"].id, "si_gls_p90", window=5)
    assert len(trend["events"]) == 1
    event = trend["events"][0]
    assert event["type"] == "transfer"
    assert event["date"].startswith("2026-07-15")  # the first snapshot at the new team
    assert event["team_from"] == "Manchester City"
    assert event["team_to"] == "Liverpool"


def test_percentile_mode_serves_only_published_rows(trend_env):
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    dates = [T0 + timedelta(days=7 * i) for i in range(5)]
    snaps = []
    for i, date in enumerate(dates):
        snaps.append(_snap(db, player, team, date, {"si_gls_p90": 0.5 + 0.1 * i}))
    # Publish percentile rows for the first two dates only; leave the rest
    # unpublished (the anomaly gate: unpublished rows are never served).
    now = datetime.now(timezone.utc)
    for i, snap in enumerate(snaps[:2]):
        db.add(
            PercentileSnapshot(
                stat_snapshot_id=snap.id,
                computed_date=now,
                position_group="ST",
                league_tier="tier_1",
                metric_name="si_gls_p90",
                percentile_value=50.0 + 10.0 * i,
                index_score=None,
                is_published=True,
            )
        )
    db.commit()

    from app.queries.trend_queries import get_player_trend

    trend = get_player_trend(db, player.id, "si_gls_p90", window=10)
    pcts = [p["pct"] for p in trend["points"]]
    assert pcts == [50.0, 60.0, None, None, None]  # unpublished -> None, never guessed


def test_flagged_snapshot_is_marked(trend_env):
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    dates = [T0 + timedelta(days=7 * i) for i in range(3)]
    for i, date in enumerate(dates):
        status = "flagged" if i == 1 else "ingested"
        _snap(db, player, team, date, {"si_gls_p90": 0.5}, status=status)
    db.commit()

    from app.queries.trend_queries import get_player_trend

    trend = get_player_trend(db, player.id, "si_gls_p90", window=5)
    assert [p["anomaly"] for p in trend["points"]] == [False, True, False]


def test_validation_and_missing_player(trend_env):
    env = trend_env
    db, player, team = env["db"], env["p_a"], env["t_a"]
    _snap(db, player, team, T0, {"si_gls_p90": 0.5})
    db.commit()

    from app.queries.trend_queries import get_player_trend

    with pytest.raises(ValueError, match="unknown metric"):
        get_player_trend(db, player.id, "nope", window=5)
    with pytest.raises(ValueError, match="window"):
        get_player_trend(db, player.id, "si_gls_p90", window=3)
    assert get_player_trend(db, 999999, "si_gls_p90", window=5) is None
    # Empty player payload still reports honestly (0 of 5).
    p_empty = Player(canonical_name="No Stats", position_group="ST", external_ids={})
    db.add(p_empty)
    db.commit()
    trend = get_player_trend(db, p_empty.id, "si_gls_p90", window=5)
    assert trend["insufficient"] is True
    assert trend["available"] == 0
