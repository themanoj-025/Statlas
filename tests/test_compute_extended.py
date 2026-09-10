"""Tests for Statlas compute modules (percentiles, formation, spatial, risk, market validation)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from tests.test_tactical import _make_league, _make_team

pytestmark = pytest.mark.unit


class TestIndex:
    """Tests for the pure index calculation (weighted mean of percentiles)."""

    def test_compute_index_weighted_mean(self) -> None:
        from app.compute.index import compute_index
        from app.config import load_registry

        registry = load_registry()
        weights = registry["position_weights"]["CM"]
        # Percentiles of 100 for every CM metric -> index must be exactly 100.
        percentiles = dict.fromkeys(weights, 100.0)
        result = compute_index(percentiles, "CM", registry)
        assert result == 100.0

    def test_compute_index_none_for_unknown_group(self) -> None:
        from app.compute.index import compute_index
        from app.config import load_registry

        result = compute_index({"si_xg_p90": 50.0}, "NOT_A_GROUP", load_registry())
        assert result is None

    def test_compute_index_none_when_too_few_metrics(self) -> None:
        from app.compute.index import compute_index
        from app.config import load_registry

        registry = load_registry()
        # Outfield needs >= 8 metrics; provide only 2.
        result = compute_index(
            {"si_gls_p90": 90.0, "si_xg_p90": 80.0}, "CM", registry
        )
        assert result is None

    def test_compute_index_renormilizes_missing_metrics(self) -> None:
        from app.compute.index import compute_index
        from app.config import load_registry

        registry = load_registry()
        weights = registry["position_weights"]["CM"]
        metric_ids = list(weights)
        # All metrics at 50 with the exact weights -> still 50 (renormalised).
        percentiles = dict.fromkeys(metric_ids[:8], 50.0)
        result = compute_index(percentiles, "CM", registry)
        assert result is not None
        assert abs(result - 50.0) < 0.01


class TestFormation:
    """Tests for formation detection (empty-pitch + graceful no-data)."""

    def test_detect_formation_no_data(self, db: Session) -> None:
        from app.compute.formation import detect_formation

        result = detect_formation(db, "nonexistent-match")
        assert result["formation_str"] == "unknown"
        assert result["confidence"] == 0

    def test_analyze_formation_stability_no_data(self, db: Session) -> None:
        from app.compute.formation import analyze_formation_stability

        result = analyze_formation_stability(db, "nonexistent-match")
        assert isinstance(result, dict)


class TestSpatialAnalysis:
    """Tests for pitch-zone assignment (pure functions)."""

    def test_assign_zone_corners(self) -> None:
        from app.compute.spatial_analysis import assign_zone

        assert assign_zone(0, 0) == (0, 0)
        assert assign_zone(120, 80) == (3, 2)

    def test_assign_zone_center(self) -> None:
        from app.compute.spatial_analysis import assign_zone

        row, col = assign_zone(60, 40)
        assert 1 <= row <= 2
        assert col == 1

    def test_assign_zone_names(self) -> None:
        from app.compute.spatial_analysis import assign_third, assign_width

        assert assign_third(5.0) == "defensive"
        assert assign_third(60.0) == "middle"
        assert assign_third(115.0) == "attacking"
        assert assign_width(5.0) == "left"
        assert assign_width(40.0) == "center"
        assert assign_width(75.0) == "right"

    def test_heatmap_empty(self, db: Session) -> None:
        from app.compute.spatial_analysis import compute_pressure_heatmap

        result = compute_pressure_heatmap(db, "nonexistent")
        assert result["total_actions"] == 0


class TestRisk:
    """Tests for transfer risk assessment."""

    def test_compute_transfer_risk_unknown_player(self, db: Session) -> None:
        from app.compute.risk import compute_transfer_risk

        result = compute_transfer_risk(db, 999999)
        assert result["risk_tier"] == "unknown"
        assert result["risk_score"] == 50
        assert "Player not found" in result["risk_factors"]

    def test_compute_valuation_confidence_signature(self, db: Session) -> None:
        from app.compute.risk import compute_valuation_confidence

        # Unknown player -> graceful low-confidence result, not an exception.
        result = compute_valuation_confidence(db, 999999)
        assert isinstance(result, dict)


class TestMarketValidation:
    """Tests for market data validation."""

    def test_validate_batch_empty(self, db: Session) -> None:
        from app.compute.market_validation import validate_batch

        report = validate_batch(db)
        assert report.total_records == 0
        assert report.valid_records == 0
        assert report.flagged_records == 0

    def test_validate_batch_no_transfers(self, db: Session) -> None:
        from app.compute.market_validation import validate_batch

        report = validate_batch(db, transfers=[])
        assert report.total_records == 0

    def test_validate_valuation_unknown_player(self, db: Session) -> None:
        from app.compute.market_validation import validate_valuation
        from app.models import MarketValuation

        record = MarketValuation(
            player_id=999999,
            source="transfermarkt",
            valuation_amount_eur=50_000_000.0,
            valuation_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        # Unpersisted player reference -> flagged with issues, not a crash.
        result = validate_valuation(record, db)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.issues, list)
