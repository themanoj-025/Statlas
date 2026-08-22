"""Activity tracking — Phase 13 Part A.

Logs user actions (viewed, created, edited, etc.) to the activity_log table.
Deduplication: same user + same entity within 60 seconds = no duplicate.
This is the single source of truth for "recently viewed" across the product.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import ActivityLog

__all__ = ["log_activity"]

DEDUP_WINDOW_SECONDS = 60


def log_activity(
    db: Session,
    *,
    user_id: int,
    entity_type: str,
    entity_id: int,
    action_type: str,
    metadata: dict | None = None,
) -> bool:
    """Log a user activity event.

    Returns True if the event was logged, False if deduplicated.

    Deduplication rule (Phase 13 A2): if the same user performed the same
    action on the same entity within DEDUP_WINDOW_SECONDS, the duplicate is
    silently skipped.  This prevents "recently viewed" from becoming a list
    of one player viewed 10 times during rapid page-back navigation.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=DEDUP_WINDOW_SECONDS)

    recent = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.entity_type == entity_type,
            ActivityLog.entity_id == entity_id,
            ActivityLog.action_type == action_type,
            ActivityLog.performed_at > cutoff,
        )
        .first()
    )

    if recent is not None:
        return False

    db.add(
        ActivityLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            metadata_=metadata,
        )
    )
    # Commit is handled by the session_scope context manager — calling
    # db.commit() here would flush prematurely when nested inside another
    # session_scope block (e.g. the player profile endpoint).
    return True
