"""Cleanup utility for expired sessions and tokens.

Run periodically (e.g., daily cron or as part of weekly_refresh) to prevent
unbounded table growth in session_tokens, password_reset_tokens,
email_verification_tokens, and analytics_events (90-day retention).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

__all__ = ["cleanup_expired_tokens", "cleanup_old_analytics"]


def cleanup_expired_tokens(db: Session) -> dict[str, int]:
    """Delete expired and revoked session tokens, used password-reset tokens,
    and used email-verification tokens.

    Returns counts of deleted rows per table.
    """
    from app.models import (
        EmailVerificationToken,
        PasswordResetToken,
        SessionToken,
    )

    now = datetime.now(timezone.utc)
    stats: dict[str, int] = {}

    # Expired or revoked session tokens — batch delete avoids loading all
    # rows into memory (matches the pattern in cleanup_old_analytics).
    stats["session_tokens"] = (
        db.query(SessionToken)
        .filter(
            (SessionToken.expires_at < now) | (SessionToken.revoked_at.isnot(None))
        )
        .delete(synchronize_session=False)
    )

    # Used or expired password-reset tokens
    stats["password_reset_tokens"] = (
        db.query(PasswordResetToken)
        .filter(
            (PasswordResetToken.used_at.isnot(None))
            | (PasswordResetToken.expires_at < now)
        )
        .delete(synchronize_session=False)
    )

    # Used or expired email-verification tokens
    stats["email_verification_tokens"] = (
        db.query(EmailVerificationToken)
        .filter(
            (EmailVerificationToken.used_at.isnot(None))
            | (EmailVerificationToken.expires_at < now)
        )
        .delete(synchronize_session=False)
    )

    db.commit()

    total = sum(stats.values())
    if total > 0:
        logger.info("Token cleanup: removed %d expired rows %s", total, stats)
    return stats


def cleanup_old_analytics(db: Session, retention_days: int = 90) -> dict[str, int]:
    """Delete analytics_events older than retention_days (Constitution Part E3:
    raw events retained 90 days)."""
    from app.models import AnalyticsEvent

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    old_events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    if old_events > 0:
        logger.info("Analytics cleanup: removed %d events older than %d days", old_events, retention_days)
    return {"analytics_events": old_events}
