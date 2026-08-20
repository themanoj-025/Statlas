"""Statlas accounts + access gating (Phase 4 — Part A).

Minimal email/password auth built on stdlib only:
- Passwords: PBKDF2-HMAC-SHA256, per-user random salt, 600k iterations.
  Never plaintext (Constitution §4 security; Part D3).
- Sessions: the token VALUE is never stored — only its SHA-256 hash, so a
  database leak cannot be replayed as a session. Expiry enforced at lookup.
- API keys (Part C) share the same hashed-value principle via auth.generate_token.
- Access gating: `has_pro_access` is THE single function every feature gate
  calls. It reads the subscriptions table (never scattered flags) and honours
  the grace period so a first payment failure does not cut access abruptly.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import SessionToken, Subscription, User

PBKDF2_ITERATIONS = 600_000
TOKEN_BYTES = 32  # 256-bit session / API key values


# ---------------------------------------------------------------------------
# Password hashing (Part A auth; D3: never plaintext)
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with a random 16-byte salt, `iterations$salt$hash`."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison against a `hash_password` value."""
    try:
        iterations, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, int(iterations)
    )
    return hmac.compare_digest(actual, expected)


# ---------------------------------------------------------------------------
# Tokens (sessions + API keys) — only hashes stored
# ---------------------------------------------------------------------------


def generate_token() -> str:
    """Random URL-safe token; return the raw value (the ONLY time it exists)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """SHA-256 hex of a token value — what is persisted and looked up."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def create_session(db: Session, user_id: int) -> tuple[str, datetime]:
    """Create a session row; returns (raw_token, expires_at). The raw token is
    returned exactly once — the DB stores only its hash."""
    settings = get_settings()
    raw = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.session_ttl_hours
    )
    db.add(
        SessionToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=expires_at,
        )
    )
    db.commit()
    return raw, expires_at


def user_from_session(db: Session, raw_token: str | None) -> User | None:
    """Resolve a session token to its user, enforcing expiry + revocation."""
    if not raw_token:
        return None
    row = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == hash_token(raw_token))
        .first()
    )
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.now(timezone.utc)
    if row.expires_at.tzinfo is None:
        row.expires_at = row.expires_at.replace(tzinfo=timezone.utc)
    if row.expires_at < now:
        return None
    return db.get(User, row.user_id)


def revoke_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == hash_token(raw_token))
        .first()
    )
    if row is not None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()


# ---------------------------------------------------------------------------
# Subscription / access gating (Part A4 — the single gate)
# ---------------------------------------------------------------------------


def current_subscription(db: Session, user_id: int) -> Subscription | None:
    """The user's active-or-relevant subscription row, or None."""
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id)
        .order_by(Subscription.id.desc())
        .first()
    )


def _utc_or_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def has_pro_access(db: Session, user_id: int) -> bool:
    """THE single access-check function — every gated feature calls this.

    Grants Pro when the subscription is active/trialing, or past_due within
    the grace period (dunning retries in flight), and the period has not
    elapsed. Canceled = no access (end-of-period retention is handled by the
    UI copy; the webhook sets canceled + period_end so access persists to the
    period boundary via status check below).
    """
    sub = current_subscription(db, user_id)
    if sub is None:
        return False
    if sub.status in ("active", "trialing"):
        return True
    if sub.status == "past_due":
        grace = _utc_or_naive(sub.grace_period_end)
        return grace is not None and grace > datetime.now(timezone.utc)
    if sub.status == "canceled":
        # End-of-period retention: access lasts until current_period_end
        # (standard SaaS practice, Part A5) — after that, revoked.
        period_end = _utc_or_naive(sub.current_period_end)
        if period_end is not None and period_end > datetime.now(timezone.utc):
            return True
        return False
    return False


def effective_plan(db: Session, user_id: int) -> str:
    """\"free\" | \"pro\" | \"api_business\" for quota/limit lookups.

    Free users may still have a canceled subscription row retaining access to
    the period end — the plan for LIMIT purposes is the subscription plan while
    has_pro_access holds, otherwise free.
    """
    sub = current_subscription(db, user_id)
    if sub is None:
        return "free"
    if sub.status in ("active", "trialing"):
        return sub.plan
    if sub.status == "past_due":
        grace = _utc_or_naive(sub.grace_period_end)
        if grace is not None and grace > datetime.now(timezone.utc):
            return sub.plan
        return "free"
    if sub.status == "canceled":
        period_end = _utc_or_naive(sub.current_period_end)
        if period_end is not None and period_end > datetime.now(timezone.utc):
            return sub.plan
    return "free"


def is_session_valid(db: Session, raw_token: str | None) -> bool:
    return user_from_session(db, raw_token) is not None


def user_payload(user: User) -> dict[str, Any]:
    """Public-safe user object (no hashes)."""
    return {
        "user_id": user.id,
        "email": user.email,
        "plan": user.plan,
        "display_name": user.display_name,
        "email_verified_at": (
            user.email_verified_at.isoformat() if user.email_verified_at else None
        ),
        "account_status": user.account_status,
        "timezone": user.timezone,
        "locale": user.locale,
    }


# ---------------------------------------------------------------------------
# Password reset (Phase 12 — Part C3)
# ---------------------------------------------------------------------------

PASSWORD_RESET_TTL_MINUTES = 60


def create_password_reset_token(db: Session, user_id: int) -> str:
    """Create a single-use password-reset token. Returns the raw token
    (shown once to the user via email). The DB stores only the hash."""
    from app.models import PasswordResetToken

    raw = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=PASSWORD_RESET_TTL_MINUTES
    )
    db.add(
        PasswordResetToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=expires_at,
        )
    )
    db.commit()
    return raw


def consume_password_reset_token(db: Session, raw_token: str) -> int | None:
    """Validate and consume a password-reset token. Returns the user_id on
    success, None if invalid/expired/already-used."""
    from app.models import PasswordResetToken

    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(raw_token))
        .first()
    )
    if row is None:
        return None
    if row.used_at is not None:
        return None
    now = datetime.now(timezone.utc)
    if row.expires_at.tzinfo is None:
        row.expires_at = row.expires_at.replace(tzinfo=timezone.utc)
    if row.expires_at < now:
        return None
    row.used_at = now
    db.commit()
    return row.user_id


# ---------------------------------------------------------------------------
# Email verification (Phase 12 — Part C1)
# ---------------------------------------------------------------------------

EMAIL_VERIFICATION_TTL_MINUTES = 24 * 60  # 24 hours


def create_email_verification_token(db: Session, user_id: int) -> str:
    """Create an email-verification token. Returns the raw token."""
    from app.models import EmailVerificationToken

    raw = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=EMAIL_VERIFICATION_TTL_MINUTES
    )
    db.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=expires_at,
        )
    )
    db.commit()
    return raw


def consume_email_verification_token(db: Session, raw_token: str) -> int | None:
    """Validate and consume an email-verification token. Returns user_id on
    success, None if invalid/expired/already-used."""
    from app.models import EmailVerificationToken

    row = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == hash_token(raw_token))
        .first()
    )
    if row is None:
        return None
    if row.used_at is not None:
        return None
    now = datetime.now(timezone.utc)
    if row.expires_at.tzinfo is None:
        row.expires_at = row.expires_at.replace(tzinfo=timezone.utc)
    if row.expires_at < now:
        return None
    row.used_at = now
    db.commit()
    return row.user_id


# ---------------------------------------------------------------------------
# Login rate limiting (Phase 12 — Part C2)
# ---------------------------------------------------------------------------

_LOGIN_FAILURES: dict[str, list[datetime]] = {}  # email -> [attempt_times]
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_MINUTES = 10
LOGIN_LOCKOUT_MINUTES = 15


def _clean_failures(email: str) -> None:
    """Remove failures older than the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    _LOGIN_FAILURES[email] = [t for t in _LOGIN_FAILURES.get(email, []) if t > cutoff]


def record_login_failure(email: str) -> None:
    """Record a failed login attempt."""
    _LOGIN_FAILURES.setdefault(email, []).append(datetime.now(timezone.utc))


def clear_login_failures(email: str) -> None:
    """Clear failures on successful login."""
    _LOGIN_FAILURES.pop(email, None)


def is_login_locked(email: str) -> tuple[bool, int]:
    """Check if an account is locked out. Returns (locked, retry_after_seconds)."""
    _clean_failures(email)
    failures = _LOGIN_FAILURES.get(email, [])
    if len(failures) < LOGIN_MAX_FAILURES:
        return False, 0
    # Lockout until the oldest failure in the window + lockout period
    oldest = min(failures)
    unlock_at = oldest + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
    now = datetime.now(timezone.utc)
    if now < unlock_at:
        retry_after = int((unlock_at - now).total_seconds())
        return True, max(retry_after, 1)
    # Lockout expired — clear and allow
    _LOGIN_FAILURES.pop(email, None)
    return False, 0
