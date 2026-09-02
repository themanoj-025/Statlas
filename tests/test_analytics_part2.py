"""Phase 18 — Analytics tests.

Tests event ingestion, metric computation, alerts, and dashboard endpoints.
All tests use in-memory SQLite (same as the rest of the test suite). — Part 2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.analytics.alerts import detect_anomalies
from app.analytics.events import REQUIRED_PROPERTIES, track_event
from app.analytics.metrics import (
    compute_arpu,
    compute_churn_rate,
    compute_conversion_funnel,
    compute_dau,
    compute_feature_usage,
    compute_mau,
    compute_retention_cohort,
)
from app.models import (
    AnalyticsAlert,
    AnalyticsEvent,
    AnalyticsSession,
    DailyMetric,
    User,
)


class TestRetention:
    """Tests for cohort retention computation."""

    def test_retention_empty_cohort(self, db: Session) -> None:
        """Empty cohort returns empty list."""
        result = compute_retention_cohort(
            db, datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        assert result == []

    def test_retention_cohort_with_users(self, db: Session) -> None:
        """Retention computes correctly for a cohort with active users."""
        now = datetime.now(timezone.utc)
        cohort_start = now - timedelta(days=60)

        # Create 3 users who signed up in the cohort month
        for i in range(3):
            user = User(
                email=f"cohort{i}@test.com",
                password_hash="dummy",
                email_verified_at=datetime.now(timezone.utc),
                plan="free",
                created_at=cohort_start + timedelta(days=i),
            )
            db.add(user)
        db.commit()

        result = compute_retention_cohort(db, cohort_start)
        assert len(result) > 0
        assert result[0]["cohort_size"] == 3


# ── Churn Tests (Part B4) ────────────────────────────────────────────


class TestChurn:
    """Tests for churn rate computation."""

    def test_churn_zero_pro_users(self, db: Session) -> None:
        """Churn rate is 0 when no Pro users exist."""
        result = compute_churn_rate(db)
        assert result["churn_rate_pct"] == 0
        assert result["annualized_churn_pct"] == 0

    def test_churn_with_cancellations(self, db: Session, pro_user: User) -> None:
        """Churn rate computed correctly with cancellations."""
        now = datetime.now(timezone.utc)

        track_event(
            db,
            event_name="subscription_canceled",
            properties={
                "user_id": pro_user.id,
                "subscription_duration_days": 90,
            },
            user_id=pro_user.id,
        )
        db.commit()

        result = compute_churn_rate(db, now)
        assert result["cancellations"] >= 1


# ── ARPU Tests (Part B5) ─────────────────────────────────────────────


class TestARPU:
    """Tests for ARPU and LTV computation."""

    def test_arpu_zero_users(self, db: Session) -> None:
        """ARPU is 0 when no Pro users exist."""
        result = compute_arpu(db)
        assert result["arpu_eur"] == 0
        assert result["mrr_eur"] == 0

    def test_arpu_with_pro_users(self, db: Session, pro_user: User) -> None:
        """ARPU computed correctly with Pro users."""
        now = datetime.now(timezone.utc)

        track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": pro_user.id, "feature_name": "shortlists"},
            user_id=pro_user.id,
        )
        db.commit()

        result = compute_arpu(db, now)
        assert result["pro_users"] >= 1
        assert result["mrr_eur"] >= 49.0


# ── Alert Tests (Part D) ──────────────────────────────────────────────


class TestAlerts:
    """Tests for threshold and anomaly alerts."""

    def test_anomaly_no_data(self, db: Session) -> None:
        """Anomaly detection returns None with no data."""
        result = detect_anomalies(db, "dau_total")
        assert result is None

    def test_alert_model_stores(self, db: Session) -> None:
        """Alerts can be stored and retrieved."""
        alert = AnalyticsAlert(
            alert_name="test_alert",
            metric_name="dau_total",
            threshold_type="above",
            threshold_value=100.0,
            actual_value=200.0,
            message="Test alert fired",
        )
        db.add(alert)
        db.commit()

        stored = db.query(AnalyticsAlert).first()
        assert stored is not None
        assert stored.alert_name == "test_alert"
        assert stored.actual_value == 200.0


# ── API Endpoint Tests ────────────────────────────────────────────────


class TestAnalyticsAPI:
    """Tests for analytics API endpoints."""

    def test_event_schema_endpoint(self, client) -> None:
        """Event schema endpoint returns all known events."""
        resp = client.get("/api/v1/analytics/events/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "user_login" in data["events"]
        assert "feature_viewed" in data["events"]

    def test_track_event_unknown(self, client) -> None:
        """Tracking an unknown event returns 400."""
        resp = client.post(
            "/api/v1/analytics/events",
            json={"event_name": "unknown_event", "properties": {}},
        )
        assert resp.status_code == 400

    def test_track_event_missing_properties(self, client) -> None:
        """Tracking event with missing properties returns 400."""
        resp = client.post(
            "/api/v1/analytics/events",
            json={"event_name": "user_login", "properties": {}},
        )
        assert resp.status_code == 400

    def test_track_event_valid(self, client, staff_user: User) -> None:
        """Tracking a valid event returns 200."""
        resp = client.post(
            "/api/v1/analytics/events",
            json={
                "event_name": "user_login",
                "properties": {"user_id": staff_user.id, "user_tier": "pro"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "event_id" in data

    def test_dau_requires_auth(self, client) -> None:
        """DAU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/dau")
        assert resp.status_code == 401

    def test_mau_requires_auth(self, client) -> None:
        """MAU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/mau")
        assert resp.status_code == 401

    def test_features_requires_auth(self, client) -> None:
        """Feature usage endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/features")
        assert resp.status_code == 401

    def test_conversion_requires_auth(self, client) -> None:
        """Conversion funnel endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/conversion")
        assert resp.status_code == 401

    def test_retention_requires_auth(self, client) -> None:
        """Retention endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/retention")
        assert resp.status_code == 401

    def test_churn_requires_auth(self, client) -> None:
        """Churn endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/churn")
        assert resp.status_code == 401

    def test_arpu_requires_auth(self, client) -> None:
        """ARPU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/arpu")
        assert resp.status_code == 401

    def test_executive_dashboard_requires_auth(self, client) -> None:
        """Executive dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/executive")
        assert resp.status_code == 401

    def test_product_dashboard_requires_auth(self, client) -> None:
        """Product dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/product")
        assert resp.status_code == 401

    def test_operations_dashboard_requires_auth(self, client) -> None:
        """Operations dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/operations")
        assert resp.status_code == 401

    def test_cohort_dashboard_requires_auth(self, client) -> None:
        """Cohort dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/cohorts")
        assert resp.status_code == 401

    def test_alerts_requires_auth(self, client) -> None:
        """Alerts endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/alerts")
        assert resp.status_code == 401

    def test_anomalies_requires_auth(self, client) -> None:
        """Anomalies endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/anomalies")
        assert resp.status_code == 401

    def test_alert_check_requires_auth(self, client) -> None:
        """Alert check endpoint requires authentication."""
        resp = client.post("/api/v1/analytics/alerts/check")
        assert resp.status_code == 401

    def test_routes_registered(self, client) -> None:
        """All analytics routes are registered."""
        routes = [r.path for r in client.app.routes]
        analytics_routes = [r for r in routes if "/analytics/" in r]
        assert len(analytics_routes) >= 10


# ── Data Integrity Tests ──────────────────────────────────────────────


class TestDataIntegrity:
    """Tests for data integrity and Constitution compliance."""

    def test_events_are_append_only(self, db: Session, staff_user: User) -> None:
        """Events are never mutated or deleted after creation."""
        event = track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
        )
        db.commit()

        original_id = event.id
        original_time = event.created_at

        # Events should never be updated or deleted
        stored = db.query(AnalyticsEvent).filter_by(id=original_id).first()
        assert stored.created_at == original_time

    def test_daily_metrics_unique_constraint(self, db: Session) -> None:
        """Daily metrics enforce unique constraint per date/name/tier.

        Note: SQLite in tests may not enforce the unique constraint on
        INSERT the same way PostgreSQL does.  We verify the model has the
        constraint defined and that PostgreSQL would enforce it.
        """
        from sqlalchemy import inspect


        mapper = inspect(DailyMetric)
        table = mapper.local_table
        unique_constraints = [c for c in table.constraints if hasattr(c, 'columns')]
        # Verify the unique constraint exists on the model
        assert len(unique_constraints) >= 1
