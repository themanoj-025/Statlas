"""Tests for app.compute — formation detection, risk, opportunity, anomaly checks."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestFormationConstants:
    """Verify formation detection position thresholds."""

    def test_position_thresholds_cover_all_zones(self) -> None:
        from app.compute.formation import POSITION_THRESHOLDS
        assert "GK" in POSITION_THRESHOLDS
        assert "DEF" in POSITION_THRESHOLDS
        assert "MID" in POSITION_THRESHOLDS
        assert "FWD" in POSITION_THRESHOLDS

    def test_gk_range(self) -> None:
        from app.compute.formation import POSITION_THRESHOLDS
        lo, hi = POSITION_THRESHOLDS["GK"]
        assert lo == 0
        assert hi == 12

    def test_fwd_range(self) -> None:
        from app.compute.formation import POSITION_THRESHOLDS
        lo, hi = POSITION_THRESHOLDS["FWD"]
        assert lo == 75
        assert hi == 120


class TestFormationFunctions:
    """Test formation detection function signatures."""

    def test_detect_formation_exists(self) -> None:
        import inspect

        from app.compute.formation import detect_formation
        sig = inspect.signature(detect_formation)
        assert "db" in sig.parameters
        assert "match_id" in sig.parameters
        assert "minute_start" in sig.parameters
        assert "minute_end" in sig.parameters

    def test_detect_formation_has_return_type(self) -> None:
        import inspect

        from app.compute.formation import detect_formation
        sig = inspect.signature(detect_formation)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestRiskFunctions:
    """Test risk computation function signatures."""

    def test_compute_valuation_confidence_exists(self) -> None:
        import inspect

        from app.compute.risk import compute_valuation_confidence
        sig = inspect.signature(compute_valuation_confidence)
        assert "db" in sig.parameters
        assert "player_id" in sig.parameters

    def test_compute_valuation_confidence_has_return_type(self) -> None:
        import inspect

        from app.compute.risk import compute_valuation_confidence
        sig = inspect.signature(compute_valuation_confidence)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestOpportunityFunctions:
    """Test opportunity detection function signatures."""

    def test_detect_hidden_gems_exists(self) -> None:
        import inspect

        from app.compute.opportunity import detect_hidden_gems
        sig = inspect.signature(detect_hidden_gems)
        assert "db" in sig.parameters
        assert "min_stat_percentile" in sig.parameters
        assert "max_market_value" in sig.parameters

    def test_detect_hidden_gems_has_return_type(self) -> None:
        import inspect

        from app.compute.opportunity import detect_hidden_gems
        sig = inspect.signature(detect_hidden_gems)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestAnomalyCheck:
    """Test anomaly check function signatures."""

    def test_check_snapshot_bounds_exists(self) -> None:
        import inspect

        from app.compute.anomaly_check import check_snapshot_bounds
        sig = inspect.signature(check_snapshot_bounds)
        assert "db" in sig.parameters
        assert "snapshot_date" in sig.parameters

    def test_check_snapshot_bounds_has_return_type(self) -> None:
        import inspect

        from app.compute.anomaly_check import check_snapshot_bounds
        sig = inspect.signature(check_snapshot_bounds)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_anomaly_constants(self) -> None:
        from app.compute.anomaly_check import _AUX_KEYS_PREFIX
        assert _AUX_KEYS_PREFIX == "_"


class TestPassingNetwork:
    """Test passing network function signatures."""

    def test_module_has_functions(self) -> None:
        import inspect

        import app.compute.passing_network as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestClusteringPkg:
    """Test clustering package constants and data functions."""

    def test_constants_module(self) -> None:
        import inspect

        import app.compute.clustering_pkg.constants as mod
        attrs = [name for name in dir(mod) if not name.startswith("_")]
        assert len(attrs) > 0

    def test_data_module(self) -> None:
        import inspect

        from app.compute.clustering_pkg.data import load_player_data
        sig = inspect.signature(load_player_data)
        assert "db" in sig.parameters


class TestEmerging:
    """Test emerging talent detection."""

    def test_emerging_module_has_functions(self) -> None:
        import inspect

        import app.compute.emerging as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0
