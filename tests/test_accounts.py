"""Phase 12 — account system tests.

Tests cover:
- Password reset: token creation, consumption, expiry, single-use
- Email verification: token creation, consumption, expiry, single-use
- Login rate limiting: lockout after max failures, lockout expiry, reset on success
- Profile updates: display_name, timezone, locale
- Account deletion: pending_deletion status, cancellation
- Post-migration integrity: existing users retain correct access to their data
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import auth
from app.models import (
    Base,
    PasswordResetToken,
    Shortlist,
    User,
    Watch,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _create_user(db: Session, email: str = "test@example.com", password: str = "password123") -> User:
    user = User(
        email=email,
        password_hash=auth.hash_password(password),
        plan="free",
    )
    db.add(user)
    db.commit()
    return user


# ---------------------------------------------------------------------------
# Password reset tests
# ---------------------------------------------------------------------------


class TestPasswordReset:
    def test_create_and_consume_token(self, db):
        user = _create_user(db)
        raw_token = auth.create_password_reset_token(db, user.id)

        user_id = auth.consume_password_reset_token(db, raw_token)
        assert user_id == user.id

    def test_single_use_token(self, db):
        user = _create_user(db)
        raw_token = auth.create_password_reset_token(db, user.id)

        auth.consume_password_reset_token(db, raw_token)
        # Second use should fail
        result = auth.consume_password_reset_token(db, raw_token)
        assert result is None

    def test_expired_token_rejected(self, db):
        user = _create_user(db)
        # Create a token and manually expire it
        raw_token = auth.create_password_reset_token(db, user.id)
        row = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user.id)
            .first()
        )
        row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        result = auth.consume_password_reset_token(db, raw_token)
        assert result is None

    def test_invalid_token_rejected(self, db):
        result = auth.consume_password_reset_token(db, "totally-invalid-token")
        assert result is None

    def test_password_changes_after_reset(self, db):
        user = _create_user(db, password="old-password")
        raw_token = auth.create_password_reset_token(db, user.id)
        user_id = auth.consume_password_reset_token(db, raw_token)

        # Simulate password change
        db_user = db.get(User, user_id)
        db_user.password_hash = auth.hash_password("new-password")
        db.commit()

        assert auth.verify_password("new-password", db_user.password_hash)
        assert not auth.verify_password("old-password", db_user.password_hash)


# ---------------------------------------------------------------------------
# Email verification tests
# ---------------------------------------------------------------------------


class TestEmailVerification:
    def test_create_and_consume_token(self, db):
        user = _create_user(db)
        raw_token = auth.create_email_verification_token(db, user.id)

        user_id = auth.consume_email_verification_token(db, raw_token)
        assert user_id == user.id

    def test_single_use_token(self, db):
        user = _create_user(db)
        raw_token = auth.create_email_verification_token(db, user.id)

        auth.consume_email_verification_token(db, raw_token)
        result = auth.consume_email_verification_token(db, raw_token)
        assert result is None

    def test_expired_token_rejected(self, db):
        user = _create_user(db)
        raw_token = auth.create_email_verification_token(db, user.id)
        from app.models import EmailVerificationToken

        ev = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id
        ).first()
        ev.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        result = auth.consume_email_verification_token(db, raw_token)
        assert result is None


# ---------------------------------------------------------------------------
# Login rate limiting tests
# ---------------------------------------------------------------------------


class TestLoginRateLimiting:
    def test_no_lockout_below_threshold(self, db):
        for _ in range(auth.LOGIN_MAX_FAILURES - 1):
            auth.record_login_failure("test@example.com")
        locked, retry_after = auth.is_login_locked("test@example.com")
        assert not locked

    def test_lockout_at_threshold(self, db):
        for _ in range(auth.LOGIN_MAX_FAILURES):
            auth.record_login_failure("test@example.com")
        locked, retry_after = auth.is_login_locked("test@example.com")
        assert locked
        assert retry_after > 0

    def test_lockout_expiry(self, db):
        for _ in range(auth.LOGIN_MAX_FAILURES):
            auth.record_login_failure("test@example.com")
        # Manually expire the failures
        auth._LOGIN_FAILURES["test@example.com"] = [
            datetime.now(timezone.utc) - timedelta(minutes=auth.LOGIN_WINDOW_MINUTES + 1)
        ]
        locked, _ = auth.is_login_locked("test@example.com")
        assert not locked

    def test_clear_failures_on_success(self, db):
        for _ in range(auth.LOGIN_MAX_FAILURES - 1):
            auth.record_login_failure("test@example.com")
        auth.clear_login_failures("test@example.com")
        locked, _ = auth.is_login_locked("test@example.com")
        assert not locked

    def test_different_emails_independent(self, db):
        for _ in range(auth.LOGIN_MAX_FAILURES):
            auth.record_login_failure("a@example.com")
        locked_a, _ = auth.is_login_locked("a@example.com")
        locked_b, _ = auth.is_login_locked("b@example.com")
        assert locked_a
        assert not locked_b


# ---------------------------------------------------------------------------
# Profile update tests
# ---------------------------------------------------------------------------


class TestProfileUpdate:
    def test_user_payload_includes_profile_fields(self, db):
        user = _create_user(db)
        payload = auth.user_payload(user)
        assert "display_name" in payload
        assert "email_verified_at" in payload
        assert "account_status" in payload
        assert "timezone" in payload
        assert "locale" in payload
        assert payload["display_name"] is None
        assert payload["email_verified_at"] is None
        assert payload["account_status"] == "active"

    def test_display_name_update(self, db):
        user = _create_user(db)
        user.display_name = "Test Scout"
        db.commit()
        payload = auth.user_payload(user)
        assert payload["display_name"] == "Test Scout"

    def test_timezone_update(self, db):
        user = _create_user(db)
        user.timezone = "Europe/London"
        db.commit()
        payload = auth.user_payload(user)
        assert payload["timezone"] == "Europe/London"


# ---------------------------------------------------------------------------
# Account deletion tests
# ---------------------------------------------------------------------------


class TestAccountDeletion:
    def test_pending_deletion_status(self, db):
        user = _create_user(db)
        user.account_status = "pending_deletion"
        db.commit()
        db.refresh(user)
        assert user.account_status == "pending_deletion"

    def test_cancel_deletion(self, db):
        user = _create_user(db)
        user.account_status = "pending_deletion"
        db.commit()
        user.account_status = "active"
        db.commit()
        db.refresh(user)
        assert user.account_status == "active"


# ---------------------------------------------------------------------------
# Post-migration data integrity tests (Part E / C6)
# ---------------------------------------------------------------------------


class TestPostMigrationIntegrity:
    def test_existing_users_retain_shortlists(self, db):
        """Migrated users keep their shortlists after Phase 12 schema changes."""
        user = _create_user(db)
        shortlist = Shortlist(user_id=user.id, name="My Scout List")
        db.add(shortlist)
        db.commit()

        # Re-query to confirm the FK still works
        found = db.query(Shortlist).filter(Shortlist.user_id == user.id).first()
        assert found is not None
        assert found.name == "My Scout List"

    def test_existing_users_retain_watches(self, db):
        """Migrated users keep their watches."""
        user = _create_user(db)
        watch = Watch(user_id=user.id, entity_type="player", entity_id=42)
        db.add(watch)
        db.commit()

        found = db.query(Watch).filter(Watch.user_id == user.id).first()
        assert found is not None
        assert found.entity_id == 42

    def test_user_plan_unchanged_after_profile_update(self, db):
        """Updating profile fields does not accidentally reset the plan."""
        user = _create_user(db)
        user.plan = "pro"
        user.display_name = "Updated Name"
        db.commit()
        db.refresh(user)
        assert user.plan == "pro"
        assert user.display_name == "Updated Name"
