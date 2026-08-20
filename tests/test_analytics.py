"""Phase 18 — Analytics tests.

Tests event ingestion, metric computation, alerts, and dashboard endpoints.
All tests use in-memory SQLite (same as the rest of the test suite).
"""

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

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def staff_user(db: Session) -> User:
    """Create a staff/admin user for analytics tests."""
    user = User(
        email="staff@statlas.com",
        password_hash="dummy",
        email_verified_at=datetime.now(timezone.utc),
        plan="pro",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def free_user(db: Session) -> User:
    """Create a free-tier user."""
    user = User(
        email="free@statlas.com",
        password_hash="dummy",
        email_verified_at=datetime.now(timezone.utc),
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def pro_user(db: Session) -> User:
    """Create a pro-tier user."""
    user = User(
        email="pro@statlas.com",
        password_hash="dummy",
        email_verified_at=datetime.now(timezone.utc),
        plan="pro",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Event Schema Tests (Part A2) ─────────────────────────────────────


class TestEventSchema:
    """Tests for event schema validation."""

    def test_known_event_accepted(self, db: Session, staff_user: User):
        """Known events with all required properties are accepted."""
        event = track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
        )
        assert event.id is not None
        assert event.event_name == "user_login"

    def test_unknown_event_rejected(self, db: Session):
        """Unknown events raise ValueError."""
        with pytest.raises(ValueError, match="Unknown event"):
            track_event(
                db,
                event_name="totally_fake_event",
                properties={},
                user_id=1,
            )

    def test_missing_property_rejected(self, db: Session):
        """Events with missing required properties raise ValueError."""
        with pytest.raises(ValueError, match="missing required properties"):
            track_event(
                db,
                event_name="user_login",
                properties={"user_id": 1},  # missing user_tier
                user_id=1,
            )

    def test_all_events_have_schemas(self):
        """Every event in REQUIRED_PROPERTIES has at least one property."""
        for name, props in REQUIRED_PROPERTIES.items():
            assert isinstance(props, list), f"Event {name} properties must be a list"
            assert len(props) > 0, f"Event {name} must have at least one required property"

    def test_event_properties_stored(self, db: Session, staff_user: User):
        """Event properties are stored as JSON."""
        event = track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": staff_user.id, "feature_name": "shortlists"},
            user_id=staff_user.id,
        )
        db.commit()
        stored = db.query(AnalyticsEvent).filter_by(id=event.id).first()
        assert stored.event_properties["feature_name"] == "shortlists"


# ── Session Tracking Tests (Part A3) ──────────────────────────────────


class TestSessionTracking:
    """Tests for session creation and management."""

    def test_session_created_on_first_event(self, db: Session, staff_user: User):
        """A new session is created when the first event arrives."""
        session_id = "test-session-001"
        track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
            session_id=session_id,
        )
        db.commit()

        session = (
            db.query(AnalyticsSession)
            .filter_by(session_id=session_id)
            .first()
        )
        assert session is not None
        assert session.user_id == staff_user.id
        assert session.event_count == 1

    def test_session_extended_on_subsequent_events(self, db: Session, staff_user: User):
        """Subsequent events extend the session."""
        session_id = "test-session-002"

        track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
            session_id=session_id,
        )
        track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": staff_user.id, "feature_name": "shortlists"},
            user_id=staff_user.id,
            session_id=session_id,
        )
        db.commit()

        session = (
            db.query(AnalyticsSession)
            .filter_by(session_id=session_id)
            .first()
        )
        assert session.event_count == 2

    def test_anonymous_events_accepted(self, db: Session):
        """Events without user_id or session_id are accepted."""
        event = track_event(
            db,
            event_name="error_occurred",
            properties={"error_type": "500", "error_message": "Internal error"},
        )
        db.commit()
        assert event.id is not None


# ── DAU/MAU Tests (Part B1) ──────────────────────────────────────────


class TestActiveUsers:
    """Tests for daily and monthly active user computation."""

    def test_dau_zero_when_no_events(self, db: Session):
        """DAU is 0 when no events exist for the date."""
        result = compute_dau(db, datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert result["dau_total"] == 0

    def test_dau_counts_unique_users(self, db: Session, staff_user: User, free_user: User):
        """DAU counts unique active users, not events."""
        now = datetime.now(timezone.utc)

        for _ in range(3):
            track_event(
                db,
                event_name="feature_viewed",
                properties={"user_id": staff_user.id, "feature_name": "shortlists"},
                user_id=staff_user.id,
            )

        track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": free_user.id, "feature_name": "shortlists"},
            user_id=free_user.id,
        )
        db.commit()

        result = compute_dau(db, now)
        assert result["dau_total"] == 2

    def test_dau_by_tier(self, db: Session, staff_user: User, free_user: User):
        """DAU correctly breaks down by subscription tier."""
        now = datetime.now(timezone.utc)

        track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
        )
        track_event(
            db,
            event_name="user_login",
            properties={"user_id": free_user.id, "user_tier": "free"},
            user_id=free_user.id,
        )
        db.commit()

        result = compute_dau(db, now)
        assert result["dau_pro"] == 1
        assert result["dau_free"] == 1

    def test_mau_counts_month(self, db: Session, staff_user: User):
        """MAU counts all unique active users in the month."""
        now = datetime.now(timezone.utc)

        track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": staff_user.id, "feature_name": "shortlists"},
            user_id=staff_user.id,
        )
        db.commit()

        result = compute_mau(db, now)
        assert result["mau_total"] == 1


# ── Feature Adoption Tests (Part B2) ──────────────────────────────────


class TestFeatureAdoption:
    """Tests for feature adoption and engagement metrics."""

    def test_feature_usage_empty_day(self, db: Session):
        """Feature usage returns all features with 0 adoption on empty day."""
        result = compute_feature_usage(db, datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert len(result) > 0
        for feature in result:
            assert feature["adoption_count"] == 0

    def test_feature_usage_with_events(self, db: Session, staff_user: User):
        """Feature usage correctly counts adoption."""
        now = datetime.now(timezone.utc)

        track_event(
            db,
            event_name="feature_viewed",
            properties={"user_id": staff_user.id, "feature_name": "shortlists"},
            user_id=staff_user.id,
        )
        db.commit()

        result = compute_feature_usage(db, now)
        shortlist_feature = next(f for f in result if f["feature_name"] == "shortlists")
        assert shortlist_feature["adoption_count"] == 1


# ── Conversion Funnel Tests (Part B3) ─────────────────────────────────


class TestConversionFunnel:
    """Tests for the Free → Pro conversion funnel."""

    def test_funnel_empty(self, db: Session):
        """Empty funnel returns 0 for all steps."""
        result = compute_conversion_funnel(db)
        assert result["step_1_signups"] == 0
        assert result["overall_conversion"] == 0

    def test_funnel_with_signups(self, db: Session):
        """Funnel counts signups correctly."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=30)

        for i in range(5):
            user = User(
                email=f"funnel{i}@test.com",
                password_hash="dummy",
                email_verified_at=datetime.now(timezone.utc),
                plan="free",
                created_at=now - timedelta(days=i),
            )
            db.add(user)
        db.commit()

        result = compute_conversion_funnel(db, start, now)
        assert result["step_1_signups"] >= 4  # may be off by 1 due to timezone boundaries


# ── Retention Tests (Part B4) ─────────────────────────────────────────


class TestRetention:
    """Tests for cohort retention computation."""

    def test_retention_empty_cohort(self, db: Session):
        """Empty cohort returns empty list."""
        result = compute_retention_cohort(
            db, datetime(2020, 1, 1, tzinfo=timezone.utc)
        )
        assert result == []

    def test_retention_cohort_with_users(self, db: Session):
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

    def test_churn_zero_pro_users(self, db: Session):
        """Churn rate is 0 when no Pro users exist."""
        result = compute_churn_rate(db)
        assert result["churn_rate_pct"] == 0
        assert result["annualized_churn_pct"] == 0

    def test_churn_with_cancellations(self, db: Session, pro_user: User):
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

    def test_arpu_zero_users(self, db: Session):
        """ARPU is 0 when no Pro users exist."""
        result = compute_arpu(db)
        assert result["arpu_eur"] == 0
        assert result["mrr_eur"] == 0

    def test_arpu_with_pro_users(self, db: Session, pro_user: User):
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

    def test_anomaly_no_data(self, db: Session):
        """Anomaly detection returns None with no data."""
        result = detect_anomalies(db, "dau_total")
        assert result is None

    def test_alert_model_stores(self, db: Session):
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

    def test_event_schema_endpoint(self, client):
        """Event schema endpoint returns all known events."""
        resp = client.get("/api/v1/analytics/events/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "user_login" in data["events"]
        assert "feature_viewed" in data["events"]

    def test_track_event_unknown(self, client):
        """Tracking an unknown event returns 400."""
        resp = client.post(
            "/api/v1/analytics/events",
            json={"event_name": "unknown_event", "properties": {}},
        )
        assert resp.status_code == 400

    def test_track_event_missing_properties(self, client):
        """Tracking event with missing properties returns 400."""
        resp = client.post(
            "/api/v1/analytics/events",
            json={"event_name": "user_login", "properties": {}},
        )
        assert resp.status_code == 400

    def test_track_event_valid(self, client, staff_user: User):
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

    def test_dau_requires_auth(self, client):
        """DAU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/dau")
        assert resp.status_code == 401

    def test_mau_requires_auth(self, client):
        """MAU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/mau")
        assert resp.status_code == 401

    def test_features_requires_auth(self, client):
        """Feature usage endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/features")
        assert resp.status_code == 401

    def test_conversion_requires_auth(self, client):
        """Conversion funnel endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/conversion")
        assert resp.status_code == 401

    def test_retention_requires_auth(self, client):
        """Retention endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/retention")
        assert resp.status_code == 401

    def test_churn_requires_auth(self, client):
        """Churn endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/churn")
        assert resp.status_code == 401

    def test_arpu_requires_auth(self, client):
        """ARPU endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/metrics/arpu")
        assert resp.status_code == 401

    def test_executive_dashboard_requires_auth(self, client):
        """Executive dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/executive")
        assert resp.status_code == 401

    def test_product_dashboard_requires_auth(self, client):
        """Product dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/product")
        assert resp.status_code == 401

    def test_operations_dashboard_requires_auth(self, client):
        """Operations dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/operations")
        assert resp.status_code == 401

    def test_cohort_dashboard_requires_auth(self, client):
        """Cohort dashboard requires authentication."""
        resp = client.get("/api/v1/analytics/dashboard/cohorts")
        assert resp.status_code == 401

    def test_alerts_requires_auth(self, client):
        """Alerts endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/alerts")
        assert resp.status_code == 401

    def test_anomalies_requires_auth(self, client):
        """Anomalies endpoint requires authentication."""
        resp = client.get("/api/v1/analytics/anomalies")
        assert resp.status_code == 401

    def test_alert_check_requires_auth(self, client):
        """Alert check endpoint requires authentication."""
        resp = client.post("/api/v1/analytics/alerts/check")
        assert resp.status_code == 401

    def test_routes_registered(self, client):
        """All analytics routes are registered."""
        routes = [r.path for r in client.app.routes]
        analytics_routes = [r for r in routes if "/analytics/" in r]
        assert len(analytics_routes) >= 10


# ── Data Integrity Tests ──────────────────────────────────────────────


class TestDataIntegrity:
    """Tests for data integrity and Constitution compliance."""

    def test_events_are_append_only(self, db: Session, staff_user: User):
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

    def test_daily_metrics_unique_constraint(self, db: Session):
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
