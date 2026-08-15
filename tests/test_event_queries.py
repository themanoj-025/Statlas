"""Event-level query tests (Phase 3 — Part B).

The first test is the quality-gate assertion for the phase: a shot/pass map
UI must NEVER render for a player/competition combination without a matching
`data_coverage` confirmation (Constitution Never-List #8) — no coverage row,
no map data, no entry point.
"""
from __future__ import annotations

from app.models import DataCoverage, MatchEvent, Player, Team

COMP = "12"
SEASON = "2025/2026"


def _player(db, name="Player A"):
    league = __import__("app.models", fromlist=["League"]).League(
        slug="premier-league", name="Premier League", country="England", tier="tier_1"
    )
    db.add(league)
    db.flush()
    team = Team(name="Manchester City", league_id=league.id, external_ids={})
    db.add(team)
    db.flush()
    player = Player(canonical_name=name, position_group="ST", current_team_id=team.id, external_ids={})
    db.add(player)
    db.flush()
    db.commit()
    return player


def _shot(db, player, match_id="m1", outcome="Goal", xg=0.42, x=95.0, y=40.0):
    db.add(
        MatchEvent(
            match_id=match_id,
            event_id=f"{match_id}-{outcome}-{xg}",
            player_id=player.id,
            event_type="Shot",
            x_coordinate=x,
            y_coordinate=y,
            minute=30,
            outcome=outcome,
            extra={"player_name": player.canonical_name, "xg": xg, "body_part": "Right Foot"},
            source_competition_id=COMP,
            season=SEASON,
        )
    )


_pass_counter = 0


def _pass(db, player, match_id="m1", completed=True, sx=50.0, ex=70.0, pass_type="Pass"):
    global _pass_counter
    _pass_counter += 1
    db.add(
        MatchEvent(
            match_id=match_id,
            event_id=f"{match_id}-p-{_pass_counter}",
            player_id=player.id,
            event_type="Pass",
            x_coordinate=sx,
            y_coordinate=40.0,
            minute=12,
            outcome="Complete" if completed else "Incomplete",
            extra={
                "player_name": player.canonical_name,
                "end_x": ex,
                "end_y": 44.0,
                "pass_type": pass_type,
            },
            source_competition_id=COMP,
            season=SEASON,
        )
    )


def _coverage(db, *, identifier="statsbomb:12:2025", status="active"):
    db.add(
        DataCoverage(
            source="statsbomb",
            source_identifier=identifier,
            seasons_available=[SEASON],
            last_successful_scrape=None,
            status=status,
        )
    )
    db.commit()


def test_coverage_gating_without_coverage_row_never_renders(db):
    """Mandatory quality gate: events exist for the player, but the coverage
    matrix has no row -> has_coverage MUST be False (no map entry point)."""
    player = _player(db)
    _shot(db, player)
    _pass(db, player)
    db.commit()

    from app.queries.event_queries import get_player_event_coverage, get_player_events

    coverage = get_player_event_coverage(db, player.id)
    assert coverage == {"has_coverage": False, "competitions": []}

    # The data queries must also refuse the unconfirmed combination.
    assert get_player_events(db, player.id, event_type="Shot", competition_id=COMP, season=SEASON) == []
    assert get_player_events(db, player.id, event_type="Pass", competition_id=COMP, season=SEASON) == []


def test_coverage_gating_active_row_unlocks_maps(db):
    player = _player(db)
    _shot(db, player, outcome="Goal", xg=0.42)
    _shot(db, player, outcome="Saved", xg=0.05, match_id="m2")
    _pass(db, player)
    _pass(db, player, completed=False, ex=52.0)
    _coverage(db)
    db.commit()

    from app.queries.event_queries import (
        get_player_event_coverage,
        get_player_event_matches,
        get_player_events,
    )

    coverage = get_player_event_coverage(db, player.id)
    assert coverage["has_coverage"] is True
    assert coverage["competitions"][0]["competition_name"] == "Premier League"
    assert coverage["competitions"][0]["matches"] == 2

    shots = get_player_events(db, player.id, event_type="Shot", competition_id=COMP, season=SEASON)
    assert len(shots) == 2
    assert {s["outcome"] for s in shots} == {"Goal", "Saved"}
    assert {s["xg"] for s in shots} == {0.42, 0.05}
    assert all(s["x"] == 95.0 for s in shots)

    matches = get_player_event_matches(db, player.id, competition_id=COMP, season=SEASON)
    assert {m["match_id"] for m in matches} == {"m1", "m2"}

    # Match filter narrows the shot set.
    assert len(get_player_events(db, player.id, event_type="Shot", match_id="m1")) == 1


def test_coverage_status_failed_blocks_maps(db):
    player = _player(db)
    _shot(db, player)
    _coverage(db, status="failed")
    db.commit()

    from app.queries.event_queries import get_player_event_coverage

    assert get_player_event_coverage(db, player.id)["has_coverage"] is False


def test_pass_queries_and_progressive_derivation(db):
    player = _player(db)
    _pass(db, player, completed=True, sx=50.0, ex=70.0)          # +20 x -> progressive
    _pass(db, player, completed=False, sx=50.0, ex=70.0)         # incomplete, still +20
    _pass(db, player, completed=True, sx=95.0, ex=100.0)         # +5 -> not progressive
    _pass(db, player, completed=True, sx=98.0, ex=105.0)         # into box (x>=102) -> progressive
    _coverage(db)
    db.commit()

    from app.queries.event_queries import get_player_events, is_progressive_pass

    passes = get_player_events(db, player.id, event_type="Pass", competition_id=COMP, season=SEASON)
    assert len(passes) == 4
    assert all(p["end_x"] is not None for p in passes)
    # +20x (twice, complete + incomplete) and into-box are progressive; +5 is not.
    progressive = [p for p in passes if p["progressive"]]
    assert len(progressive) == 3
    assert is_progressive_pass(50.0, 60.0) is True
    assert is_progressive_pass(90.0, 95.0) is False
    assert is_progressive_pass(60.0, 55.0) is False  # backwards
    assert is_progressive_pass(None, 70.0) is False  # never assumed

    # The incomplete pass keeps its outcome so the map can encode it.
    outcomes = {p["outcome"] for p in passes}
    assert outcomes == {"Complete", "Incomplete"}


def test_competition_label_fallback(db):
    from app.queries.event_queries import competition_label, parse_statsbomb_identifier

    assert competition_label("12") == "Premier League"
    assert competition_label("9999") == "Competition 9999"  # never a guessed name
    assert parse_statsbomb_identifier("statsbomb:12:2025") == ("12", "2025")
    assert parse_statsbomb_identifier("fbref:premier-league") is None


def test_get_statsbomb_competitions_lists_only_covered(db):
    from app.queries.event_queries import get_statsbomb_competitions

    assert get_statsbomb_competitions(db) == []
    _coverage(db)
    comps = get_statsbomb_competitions(db)
    assert comps[0]["competition_id"] == "12"
    assert comps[0]["competition_name"] == "Premier League"
    assert comps[0]["seasons_available"] == [SEASON]
