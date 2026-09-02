"""Tests for Phase 17 — Tactical Intelligence modules.

Covers:
- Passing network construction and metrics (passing_network.py)
- Pitch zone assignment (spatial_analysis.py)
- Pressure/possession heatmaps (spatial_analysis.py)
- Pressure success rate (spatial_analysis.py)
- Formation detection (formation.py)
- Formation stability (formation.py)
- Formation conformity (formation.py)
- Coverage gating (has_tactical_data)
- API endpoint availability

Constitution §4: Every data-parsing function has a unit test.
Constitution §7: Testing minimum bar — critical UI paths tested.
"""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.models import (

pytestmark = pytest.mark.slow
    DataCoverage,
    League,
    MatchEvent,
    Player,
    Team,
)

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_league(db: Session) -> League:
    league = League(
        slug="champions-league",
        name="UEFA Champions League",
        country="Europe",
        tier="tier_1",
        external_ids={},
    )
    db.add(league)
    db.flush()
    return league


def _make_team(db: Session, league: League, name: str = "Team A") -> Team:
    team = Team(name=name, league_id=league.id, external_ids={})
    db.add(team)
    db.flush()
    return team


def _make_player(db: Session, team: Team, name: str = "Player A") -> Player:
    player = Player(canonical_name=name, current_team_id=team.id, position_group="CM")
    db.add(player)
    db.flush()
    return player


def _make_coverage(
    db: Session, competition_id: str = "2", season: str = "2023/2024"
) -> None:
    cov = DataCoverage(
        source="statsbomb",
        source_identifier=f"statsbomb:{competition_id}:1",
        seasons_available=[season],
        status="active",
    )
    db.add(cov)
    db.flush()


_pass_counter = 0


def _make_pass_event(
    db: Session,
    match_id: str,
    player: Player,
    *,
    x: float = 60,
    y: float = 40,
    end_x: float = 70,
    end_y: float = 35,
    minute: float = 10,
    outcome: str | None = None,
    recipient: str | None = None,
    pass_type: str | None = None,
) -> MatchEvent:
    global _pass_counter
    _pass_counter += 1
    extra = {
        "player_name": player.canonical_name,
        "end_x": end_x,
        "end_y": end_y,
        "recipient": recipient,
        "pass_type": pass_type,
        "length": math.sqrt((end_x - x) ** 2 + (end_y - y) ** 2),
    }
    ev = MatchEvent(
        match_id=match_id,
        event_id=f"{match_id}_{player.id}_pass_{_pass_counter}",
        player_id=player.id,
        event_type="Pass",
        x_coordinate=x,
        y_coordinate=y,
        minute=minute,
        outcome=outcome,
        source_competition_id="2",
        season="2023/2024",
        extra=extra,
    )
    db.add(ev)
    return ev


_def_counter = 0


def _make_defensive_event(
    db: Session,
    match_id: str,
    player: Player,
    *,
    x: float = 30,
    y: float = 40,
    minute: float = 5,
    event_type: str = "Pressure",
) -> MatchEvent:
    global _def_counter
    _def_counter += 1
    extra = {"player_name": player.canonical_name}
    ev = MatchEvent(
        match_id=match_id,
        event_id=f"{match_id}_{player.id}_{event_type}_{_def_counter}",
        player_id=player.id,
        event_type=event_type,
        x_coordinate=x,
        y_coordinate=y,
        minute=minute,
        source_competition_id="2",
        season="2023/2024",
        extra=extra,
    )
    db.add(ev)
    return ev


# ---------------------------------------------------------------------------
# Zone assignment tests
# ---------------------------------------------------------------------------


class TestZoneAssignment:
    """C1 — Pitch zone definitions."""

    def test_defensive_left(self) -> None:
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(10, 10) == (0, 0)
        assert assign_zone_name(10, 10) == "defensive_left"

    def test_attacking_right(self) -> None:
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(110, 70) == (3, 2)
        assert assign_zone_name(110, 70) == "attacking_right"

    def test_center_midfield(self) -> None:
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(60, 40) == (1, 1) or assign_zone(60, 40) == (2, 1)
        name = assign_zone_name(60, 40)
        assert "center" in name

    def test_third_assignment(self) -> None:
        from app.compute.spatial_analysis import assign_third

        assert assign_third(10) == "defensive"
        assert assign_third(60) == "middle"
        assert assign_third(100) == "attacking"

    def test_width_assignment(self) -> None:
        from app.compute.spatial_analysis import assign_width

        assert assign_width(5) == "left"
        assert assign_width(40) == "center"
        assert assign_width(75) == "right"

    def test_boundary_values(self) -> None:
        from app.compute.spatial_analysis import assign_zone

        assert assign_zone(0, 0) == (0, 0)
        assert assign_zone(120, 80) == (3, 2)

    def test_all_zones_covered(self) -> None:
        from app.compute.spatial_analysis import assign_zone_name

        found_zones = set()
        for x in range(0, 121, 10):
            for y in range(0, 81, 10):
                found_zones.add(assign_zone_name(x, y))
        # Should have most of the 12 zones
        assert len(found_zones) >= 10


# ---------------------------------------------------------------------------
# Passing network tests
# ---------------------------------------------------------------------------


class TestPassingNetwork:
    """B1-B2 — Network construction and metrics."""

    def test_build_network_empty(self, db: Session) -> None:
        from app.compute.passing_network import build_passing_network

        result = build_passing_network(db, "nonexistent_match")
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["total_passes"] == 0

    def test_build_network_basic(self, db: Session) -> None:
        from app.compute.passing_network import build_passing_network

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team, "Alice")
        p2 = _make_player(db, team, "Bob")

        _make_pass_event(db, "m1", p1, x=50, y=40, end_x=70, end_y=35, recipient="Bob")
        _make_pass_event(db, "m1", p1, x=50, y=40, end_x=80, end_y=30, recipient="Bob")
        _make_pass_event(
            db, "m1", p2, x=70, y=35, end_x=55, end_y=45, recipient="Alice"
        )
        db.commit()

        result = build_passing_network(db, "m1")
        assert len(result["nodes"]) == 2
        assert result["total_passes"] == 3
        # Edges: p1→p2 (2 passes), p2→p1 (1 pass)
        assert len(result["edges"]) == 2

    def test_network_metrics(self, db: Session) -> None:
        from app.compute.passing_network import (
            build_passing_network,
            compute_network_metrics,
        )

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team, "Alice")
        p2 = _make_player(db, team, "Bob")
        p3 = _make_player(db, team, "Charlie")

        # Create a triangle of passes
        for i in range(5):
            _make_pass_event(
                db,
                "m1",
                p1,
                x=50,
                y=40,
                end_x=70,
                end_y=35,
                recipient="Bob",
                minute=float(i),
            )
            _make_pass_event(
                db,
                "m1",
                p2,
                x=70,
                y=35,
                end_x=55,
                end_y=45,
                recipient="Alice",
                minute=float(i + 10),
            )
            _make_pass_event(
                db,
                "m1",
                p3,
                x=55,
                y=45,
                end_x=50,
                end_y=40,
                recipient="Alice",
                minute=float(i + 20),
            )
        db.commit()

        network = build_passing_network(db, "m1")
        metrics = compute_network_metrics(network)

        assert len(metrics["nodes"]) == 3
        for node in metrics["nodes"]:
            assert 0 <= node["degree_centrality"] <= 1
            assert 0 <= node["betweenness_centrality"] <= 1
            assert 0 <= node["clustering_coefficient"] <= 1

    def test_network_with_incomplete_passes(self, db: Session) -> None:
        from app.compute.passing_network import build_passing_network

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team, "Alice")
        _make_player(db, team, "Bob")

        # Complete pass
        _make_pass_event(db, "m1", p1, x=50, y=40, end_x=70, end_y=35, recipient="Bob")
        # Incomplete pass (should not count)
        _make_pass_event(
            db,
            "m1",
            p1,
            x=50,
            y=40,
            end_x=70,
            end_y=35,
            recipient="Bob",
            outcome="Incomplete",
        )
        db.commit()

        result = build_passing_network(db, "m1")
        # Only the complete pass should count
        assert result["total_passes"] == 1


# ---------------------------------------------------------------------------
# Tactical style detection tests
# ---------------------------------------------------------------------------


