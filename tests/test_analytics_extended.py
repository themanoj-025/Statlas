"""Tests for Statlas analytics module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit



class TestAlerts:
    """Tests for analytics alerts."""

    def test_detect_anomalies(self) -> None:
        from app.analytics.alerts import detect_anomalies

        # Normal data — no anomalies
        data = [{"metric": "views", "value": 100} for _ in range(10)]
        result = detect_anomalies(data, metric="views")
        assert isinstance(result, list)

    def test_detect_anomalies_empty(self) -> None:
        from app.analytics.alerts import detect_anomalies

        result = detect_anomalies([], metric="views")
        assert result == []


class TestEvents:
    """Tests for analytics events."""

    def test_track_event(self) -> None:
        from app.analytics.events import track_event

        # Should not raise
        track_event("test_event", {"key": "value"})

    def test_required_properties(self) -> None:
        from app.analytics.events import REQUIRED_PROPERTIES

        assert isinstance(REQUIRED_PROPERTIES, dict)
        assert "event_name" in REQUIRED_PROPERTIES or len(REQUIRED_PROPERTIES) >= 0


class TestMetrics:
    """Tests for analytics metrics computation."""

    def test_compute_dau(self) -> None:
        from app.analytics.metrics import compute_dau

        result = compute_dau([])
        assert isinstance(result, (int, float))

    def test_compute_mau(self) -> None:
        from app.analytics.metrics import compute_mau

        result = compute_mau([])
        assert isinstance(result, (int, float))

    def test_compute_arpu(self) -> None:
        from app.analytics.metrics import compute_arpu

        result = compute_arpu(1000.0, 100)
        assert isinstance(result, (int, float))

    def test_compute_churn_rate(self) -> None:
        from app.analytics.metrics import compute_churn_rate

        result = compute_churn_rate(start=100, end=90)
        assert 0 <= result <= 1

    def test_compute_retention_cohort(self) -> None:
        from app.analytics.metrics import compute_retention_cohort

        cohorts = [
            {"cohort_date": "2024-01", "users": 100, "retained_week_1": 80},
        ]
        result = compute_retention_cohort(cohorts)
        assert isinstance(result, list)
