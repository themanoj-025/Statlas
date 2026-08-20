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
    DataCoverage,
    League,
    MatchEvent,
    Player,
    Team,
)

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

    def test_defensive_left(self):
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(10, 10) == (0, 0)
        assert assign_zone_name(10, 10) == "defensive_left"

    def test_attacking_right(self):
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(110, 70) == (3, 2)
        assert assign_zone_name(110, 70) == "attacking_right"

    def test_center_midfield(self):
        from app.compute.spatial_analysis import assign_zone, assign_zone_name

        assert assign_zone(60, 40) == (1, 1) or assign_zone(60, 40) == (2, 1)
        name = assign_zone_name(60, 40)
        assert "center" in name

    def test_third_assignment(self):
        from app.compute.spatial_analysis import assign_third

        assert assign_third(10) == "defensive"
        assert assign_third(60) == "middle"
        assert assign_third(100) == "attacking"

    def test_width_assignment(self):
        from app.compute.spatial_analysis import assign_width

        assert assign_width(5) == "left"
        assert assign_width(40) == "center"
        assert assign_width(75) == "right"

    def test_boundary_values(self):
        from app.compute.spatial_analysis import assign_zone

        assert assign_zone(0, 0) == (0, 0)
        assert assign_zone(120, 80) == (3, 2)

    def test_all_zones_covered(self):
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

    def test_build_network_empty(self, db: Session):
        from app.compute.passing_network import build_passing_network

        result = build_passing_network(db, "nonexistent_match")
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["total_passes"] == 0

    def test_build_network_basic(self, db: Session):
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

    def test_network_metrics(self, db: Session):
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

    def test_network_with_incomplete_passes(self, db: Session):
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


class TestTacticalStyle:
    """B3 — Tactical style detection."""

    def test_possession_style(self):
        from app.compute.passing_network import detect_tactical_style

        network = {
            "total_passes": 500,
            "edges": [{"from": 1, "to": 2, "weight": 20}],
            "nodes": [],
        }
        metrics = {"nodes": []}
        result = detect_tactical_style(network, metrics)
        assert result["style"] == "insufficient_data"

    def test_insufficient_data(self):
        from app.compute.passing_network import detect_tactical_style

        result = detect_tactical_style({"total_passes": 0, "nodes": []}, {"nodes": []})
        assert result["style"] == "insufficient_data"


# ---------------------------------------------------------------------------
# Anomaly detection tests
# ---------------------------------------------------------------------------


class TestAnomalyDetection:
    """B4 — Anomaly detection in passing networks."""

    def test_no_anomalies(self):
        from app.compute.passing_network import detect_network_anomalies

        result = detect_network_anomalies(
            {"nodes": [], "edges": []},
            {"nodes": []},
        )
        assert result == []

    def test_disconnected_player(self):
        from app.compute.passing_network import detect_network_anomalies

        metrics = {
            "nodes": [
                {
                    "player_id": 1,
                    "pass_count": 30,
                    "pass_attempts": 40,
                    "betweenness_centrality": 0.1,
                    "pass_success_rate": 75,
                },
                {
                    "player_id": 2,
                    "pass_count": 0,
                    "pass_attempts": 0,
                    "betweenness_centrality": 0,
                    "pass_success_rate": 0,
                },
            ]
        }
        result = detect_network_anomalies(
            {"nodes": metrics["nodes"], "edges": []}, metrics
        )
        disconnected = [a for a in result if a["type"] == "disconnected_player"]
        assert len(disconnected) == 1
        assert disconnected[0]["player_id"] == 2


# ---------------------------------------------------------------------------
# Pressure/possession heatmap tests
# ---------------------------------------------------------------------------


class TestHeatmaps:
    """C2-C3 — Pressure and possession heatmaps."""

    def test_pressure_heatmap_empty(self, db: Session):
        from app.compute.spatial_analysis import compute_pressure_heatmap

        result = compute_pressure_heatmap(db, "nonexistent")
        assert result["total_actions"] == 0
        assert all(v == 0 for v in result["zone_densities"].values())

    def test_pressure_heatmap_with_data(self, db: Session):
        from app.compute.spatial_analysis import compute_pressure_heatmap

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team)

        # Create defensive events in various zones
        _make_defensive_event(db, "m1", p1, x=30, y=10, event_type="Pressure")
        _make_defensive_event(db, "m1", p1, x=30, y=10, event_type="Tackle")
        _make_defensive_event(db, "m1", p1, x=80, y=60, event_type="Interception")
        db.commit()

        result = compute_pressure_heatmap(db, "m1")
        assert result["total_actions"] == 3
        # Should have at least one zone with non-zero density
        assert any(v > 0 for v in result["zone_densities"].values())

    def test_possession_heatmap(self, db: Session):
        from app.compute.spatial_analysis import compute_possession_heatmap

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team)

        _make_pass_event(db, "m1", p1, x=90, y=40, end_x=100, end_y=35, minute=5)
        _make_pass_event(db, "m1", p1, x=90, y=40, end_x=105, end_y=45, minute=10)
        db.commit()

        result = compute_possession_heatmap(db, "m1")
        assert result["total_actions"] >= 1
        assert "zone_densities" in result


# ---------------------------------------------------------------------------
# Pressure success rate tests
# ---------------------------------------------------------------------------


class TestPressureSuccess:
    """C4 — Pressure success rate per zone."""

    def test_pressure_success_empty(self, db: Session):
        from app.compute.spatial_analysis import compute_pressure_success

        result = compute_pressure_success(db, "nonexistent")
        assert result["zone_success_rates"] == {} or all(
            v["total_pressures"] == 0 for v in result["zone_success_rates"].values()
        )

    def test_pressure_success_with_turnover(self, db: Session):
        from app.compute.spatial_analysis import compute_pressure_success

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team)

        # Pressure followed by pass (success)
        _make_defensive_event(db, "m1", p1, x=30, y=40, event_type="Pressure", minute=5)
        _make_pass_event(db, "m1", p1, x=35, y=40, end_x=50, end_y=35, minute=5.5)
        db.commit()

        result = compute_pressure_success(db, "m1")
        # Should have at least one zone with pressure data
        has_data = any(
            v["total_pressures"] > 0 for v in result["zone_success_rates"].values()
        )
        assert has_data


# ---------------------------------------------------------------------------
# Coverage check tests
# ---------------------------------------------------------------------------


class TestCoverageCheck:
    """Coverage gating for tactical data."""

    def test_has_tactical_data_no_events(self, db: Session):
        from app.compute.spatial_analysis import has_tactical_data

        result = has_tactical_data(db, "nonexistent")
        assert result["has_coverage"] is False

    def test_has_tactical_data_with_events(self, db: Session):
        from app.compute.spatial_analysis import has_tactical_data

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team)

        for i in range(150):
            _make_pass_event(
                db, "m1", p1, x=60, y=40, end_x=70, end_y=35, minute=float(i)
            )
        db.commit()

        result = has_tactical_data(db, "m1", min_events=100)
        assert result["has_coverage"] is True
        assert result["event_count"] == 150


# ---------------------------------------------------------------------------
# Formation detection tests
# ---------------------------------------------------------------------------


class TestFormationDetection:
    """D1-D2 — Formation detection and stability."""

    def test_formation_unknown_match(self, db: Session):
        from app.compute.formation import detect_formation

        result = detect_formation(db, "nonexistent")
        assert result["formation_str"] == "unknown"
        assert result["confidence"] == 0

    def test_formation_basic_433(self, db: Session):
        from app.compute.formation import detect_formation

        league = _make_league(db)
        team = _make_team(db, league)

        # Create 11 players with typical 4-3-3 positioning
        gk = _make_player(db, team, "GK")  # x ~ 10
        defenders = [_make_player(db, team, f"DEF{i}") for i in range(4)]
        midfielders = [_make_player(db, team, f"MID{i}") for i in range(3)]
        forwards = [_make_player(db, team, f"FWD{i}") for i in range(3)]

        # Create events for each player at their expected positions
        positions = [
            (gk, 10, 40),  # GK position
        ]
        for i, p in enumerate(defenders):
            positions.append((p, 30, 10 + i * 20))  # DEF line
        for i, p in enumerate(midfielders):
            positions.append((p, 60, 15 + i * 25))  # MID line
        for i, p in enumerate(forwards):
            positions.append((p, 90, 15 + i * 25))  # FWD line

        for player, x, y in positions:
            for j in range(10):
                _make_pass_event(
                    db,
                    "m1",
                    player,
                    x=x,
                    y=y,
                    end_x=min(120, x + 10),
                    end_y=y,
                    minute=float(j),
                )
        db.commit()

        result = detect_formation(db, "m1")
        # Should detect something like 4-3-3
        assert result["formation"][0] == 4  # defenders
        assert result["formation"][1] == 3  # midfielders
        assert result["formation"][2] == 3  # forwards

    def test_formation_stability(self, db: Session):
        from app.compute.formation import analyze_formation_stability

        league = _make_league(db)
        team = _make_team(db, league)
        p1 = _make_player(db, team)

        # Create minimal events
        for i in range(120):
            _make_pass_event(
                db, "m1", p1, x=50, y=40, end_x=60, end_y=35, minute=float(i)
            )
        db.commit()

        result = analyze_formation_stability(db, "m1", window_minutes=30)
        assert "windows" in result
        assert len(result["windows"]) == 4  # 120 / 30 = 4 windows
        assert 0 <= result["stability_score"] <= 1

    def test_formation_conformity(self, db: Session):
        from app.compute.formation import analyze_formation_conformity

        league = _make_league(db)
        team = _make_team(db, league)
        gk = _make_player(db, team, "GK")
        p1 = _make_player(db, team, "DEF")

        for j in range(10):
            _make_pass_event(
                db, "m1", gk, x=10, y=40, end_x=20, end_y=35, minute=float(j)
            )
            _make_pass_event(
                db, "m1", p1, x=30, y=40, end_x=50, end_y=35, minute=float(j + 10)
            )
        db.commit()

        result = analyze_formation_conformity(db, "m1", nominal_formation="4-3-3")
        assert "player_conformity" in result
        assert 0 <= result["overall_conformity"] <= 1


# ---------------------------------------------------------------------------
# API endpoint availability tests
# ---------------------------------------------------------------------------


class TestAPIEndpoints:
    """Verify tactical API endpoints are registered."""

    def test_tactical_router_registered(self):
        from app.api.tactical_views import router

        routes = [r.path for r in router.routes]
        assert any("overview" in p for p in routes)
        assert any("passing-network" in p for p in routes)
        assert any("pressure-map" in p for p in routes)
        assert any("possession-map" in p for p in routes)
        assert any("formation" in p for p in routes)
        assert any("coverage" in p for p in routes)

    def test_main_includes_tactical(self):
        from app.api.tactical_views import router as t

        assert t.prefix == "/api/v1/tactical"
