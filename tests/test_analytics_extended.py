"""Tests for Statlas analytics modules (alerts, events, metrics)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import DailyMetric, User

pytestmark = pytest.mark.unit


class TestAlerts:
    """Tests for analytics anomaly detection."""

    def test_detect_anomalies_no_data(self, db: Session) -> None:
        from app.analytics.alerts import detect_anomalies

        # No data at all -> None (cannot assess).
        assert detect_anomalies(db, "views") is None

    def test_detect_anomalies_insufficient_history(self, db: Session) -> None:
        from app.analytics.alerts import detect_anomalies

        now = datetime.now(timezone.utc)
        # Fewer than 7 historical values -> None (needs at least a week).
        for i in range(3):
            db.add(
                DailyMetric(
                    metric_date=now - timedelta(weeks=2 + i),
                    metric_name="views",
                    value=100.0,
                )
            )
        db.commit()
        assert detect_anomalies(db, "views") is None

    def test_detect_anomalies_stable_history(self, db: Session) -> None:
        from app.analytics.alerts import detect_anomalies

        now = datetime.now(timezone.utc)
        # 8 weeks of identical values -> no anomaly (std dev = 0).
        for i in range(1, 9):
            db.add(
                DailyMetric(
                    metric_date=now - timedelta(weeks=i),
                    metric_name="views",
                    value=100.0,
                )
            )
        db.commit()
        assert detect_anomalies(db, "views") is None


class TestEvents:
    """Tests for analytics event tracking."""

    def test_track_event(self, db: Session, pro_user: User) -> None:
        from app.analytics.events import track_event

        event = track_event(
            db,
            event_name="user_login",
            properties={"user_id": pro_user.id, "user_tier": "pro"},
            user_id=pro_user.id,
        )
        db.commit()
        assert event.event_name == "user_login"
        assert event.id is not None

    def test_track_event_unknown_rejected(self, db: Session) -> None:
        from app.analytics.events import track_event

        # Unknown events must raise ValueError (never silently accepted).
        with pytest.raises(ValueError, match="Unknown event"):
            track_event(db, event_name="definitely_not_an_event", properties={})

    def test_track_event_missing_properties_rejected(
        self, db: Session, pro_user: User
    ) -> None:
        from app.analytics.events import track_event

        with pytest.raises(ValueError):
            track_event(
                db, event_name="user_login", properties={"user_id": pro_user.id}
            )

    def test_required_properties_shape(self) -> None:
        from app.analytics.events import REQUIRED_PROPERTIES

        assert isinstance(REQUIRED_PROPERTIES, dict)
        assert "user_login" in REQUIRED_PROPERTIES
        assert "user_id" in REQUIRED_PROPERTIES["user_login"]


class TestMetrics:
    """Tests for analytics metrics computation (empty-database baselines)."""

    def test_compute_dau(self, db: Session) -> None:
        from app.analytics.metrics import compute_dau

        result = compute_dau(db)
        assert isinstance(result, dict)
        assert result["dau_total"] == 0
        assert result["dau_free"] == 0
        assert result["dau_pro"] == 0

    def test_compute_mau(self, db: Session) -> None:
        from app.analytics.metrics import compute_mau

        result = compute_mau(db)
        assert isinstance(result, dict)
        assert result["mau_total"] == 0

    def test_compute_arpu(self, db: Session) -> None:
        from app.analytics.metrics import compute_arpu

        result = compute_arpu(db)
        assert isinstance(result, dict)
        assert result["pro_users"] == 0
        assert result["mrr_eur"] == 0.0

    def test_compute_churn_rate(self, db: Session) -> None:
        from app.analytics.metrics import compute_churn_rate

        result = compute_churn_rate(db)
        assert isinstance(result, dict)
        assert result["churn_rate_pct"] == 0

    def test_compute_retention_cohort_empty(self, db: Session) -> None:
        from app.analytics.metrics import compute_retention_cohort

        result = compute_retention_cohort(db, datetime(2020, 1, 1, tzinfo=timezone.utc))
        assert result == []
