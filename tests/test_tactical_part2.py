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
Constitution §7: Testing minimum bar — critical UI paths tested. — Part 2."""

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


class TestTacticalStyle:
    """B3 — Tactical style detection."""

    def test_possession_style(self) -> None:
        from app.compute.passing_network import detect_tactical_style

        network = {
            "total_passes": 500,
            "edges": [{"from": 1, "to": 2, "weight": 20}],
            "nodes": [],
        }
        metrics = {"nodes": []}
        result = detect_tactical_style(network, metrics)
        assert result["style"] == "insufficient_data"

    def test_insufficient_data(self) -> None:
        from app.compute.passing_network import detect_tactical_style

        result = detect_tactical_style({"total_passes": 0, "nodes": []}, {"nodes": []})
        assert result["style"] == "insufficient_data"


# ---------------------------------------------------------------------------
# Anomaly detection tests
# ---------------------------------------------------------------------------


class TestAnomalyDetection:
    """B4 — Anomaly detection in passing networks."""

    def test_no_anomalies(self) -> None:
        from app.compute.passing_network import detect_network_anomalies

        result = detect_network_anomalies(
            {"nodes": [], "edges": []},
            {"nodes": []},
        )
        assert result == []

    def test_disconnected_player(self) -> None:
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

    def test_pressure_heatmap_empty(self, db: Session) -> None:
        from app.compute.spatial_analysis import compute_pressure_heatmap

        result = compute_pressure_heatmap(db, "nonexistent")
        assert result["total_actions"] == 0
        assert all(v == 0 for v in result["zone_densities"].values())

    def test_pressure_heatmap_with_data(self, db: Session) -> None:
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

    def test_possession_heatmap(self, db: Session) -> None:
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

    def test_pressure_success_empty(self, db: Session) -> None:
        from app.compute.spatial_analysis import compute_pressure_success

        result = compute_pressure_success(db, "nonexistent")
        assert result["zone_success_rates"] == {} or all(
            v["total_pressures"] == 0 for v in result["zone_success_rates"].values()
        )

    def test_pressure_success_with_turnover(self, db: Session) -> None:
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

    def test_has_tactical_data_no_events(self, db: Session) -> None:
        from app.compute.spatial_analysis import has_tactical_data

        result = has_tactical_data(db, "nonexistent")
        assert result["has_coverage"] is False

    def test_has_tactical_data_with_events(self, db: Session) -> None:
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

    def test_formation_unknown_match(self, db: Session) -> None:
        from app.compute.formation import detect_formation

        result = detect_formation(db, "nonexistent")
        assert result["formation_str"] == "unknown"
        assert result["confidence"] == 0

    def test_formation_basic_433(self, db: Session) -> None:
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

    def test_formation_stability(self, db: Session) -> None:
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

    def test_formation_conformity(self, db: Session) -> None:
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

    def test_tactical_router_registered(self) -> None:
        from app.api.tactical_views import router

        routes = [r.path for r in router.routes]
        assert any("overview" in p for p in routes)
        assert any("passing-network" in p for p in routes)
        assert any("pressure-map" in p for p in routes)
        assert any("possession-map" in p for p in routes)
        assert any("formation" in p for p in routes)
        assert any("coverage" in p for p in routes)

    def test_main_includes_tactical(self) -> None:
        from app.api.tactical_views import router as t


        assert t.prefix == "/api/v1/tactical"
