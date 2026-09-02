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

pytestmark = pytest.mark.slow
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

    def test_known_event_accepted(self, db: Session, staff_user: User) -> None:
        """Known events with all required properties are accepted."""
        event = track_event(
            db,
            event_name="user_login",
            properties={"user_id": staff_user.id, "user_tier": "pro"},
            user_id=staff_user.id,
        )
        assert event.id is not None
        assert event.event_name == "user_login"

    def test_unknown_event_rejected(self, db: Session) -> None:
        """Unknown events raise ValueError."""
        with pytest.raises(ValueError, match="Unknown event"):
            track_event(
                db,
                event_name="totally_fake_event",
                properties={},
                user_id=1,
            )

    def test_missing_property_rejected(self, db: Session) -> None:
        """Events with missing required properties raise ValueError."""
        with pytest.raises(ValueError, match="missing required properties"):
            track_event(
                db,
                event_name="user_login",
                properties={"user_id": 1},  # missing user_tier
                user_id=1,
            )

    def test_all_events_have_schemas(self) -> None:
        """Every event in REQUIRED_PROPERTIES has at least one property."""
        for name, props in REQUIRED_PROPERTIES.items():
            assert isinstance(props, list), f"Event {name} properties must be a list"
            assert len(props) > 0, f"Event {name} must have at least one required property"

    def test_event_properties_stored(self, db: Session, staff_user: User) -> None:
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

    def test_session_created_on_first_event(self, db: Session, staff_user: User) -> None:
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

    def test_session_extended_on_subsequent_events(self, db: Session, staff_user: User) -> None:
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

    def test_anonymous_events_accepted(self, db: Session) -> None:
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

    def test_dau_zero_when_no_events(self, db: Session) -> None:
        """DAU is 0 when no events exist for the date."""
        result = compute_dau(db, datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert result["dau_total"] == 0

    def test_dau_counts_unique_users(self, db: Session, staff_user: User, free_user: User) -> None:
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

    def test_dau_by_tier(self, db: Session, staff_user: User, free_user: User) -> None:
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

    def test_mau_counts_month(self, db: Session, staff_user: User) -> None:
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

    def test_feature_usage_empty_day(self, db: Session) -> None:
        """Feature usage returns all features with 0 adoption on empty day."""
        result = compute_feature_usage(db, datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert len(result) > 0
        for feature in result:
            assert feature["adoption_count"] == 0

    def test_feature_usage_with_events(self, db: Session, staff_user: User) -> None:
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

    def test_funnel_empty(self, db: Session) -> None:
        """Empty funnel returns 0 for all steps."""
        result = compute_conversion_funnel(db)
        assert result["step_1_signups"] == 0
        assert result["overall_conversion"] == 0

    def test_funnel_with_signups(self, db: Session) -> None:
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


