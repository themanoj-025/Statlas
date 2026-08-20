"""Phase 18 — Event ingestion pipeline.

Every tracked event enters here.  Events are append-only (Constitution §3).
Schema validation happens at write time — bad events are rejected, never
silently coerced.

Part A1-A4 of the Phase 18 execution prompt.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import AnalyticsEvent, AnalyticsSession

# Session timeout: 30 minutes of inactivity ends a session (Part A3).
SESSION_TIMEOUT_MINUTES = 30

# ── Known event schemas ───────────────────────────────────────────────
# Each event name maps to its required properties.  Events not in this
# registry are rejected — no silent unknown events (Constitution §6.5).

REQUIRED_PROPERTIES: dict[str, list[str]] = {
    "user_login": ["user_id", "user_tier"],
    "user_signup": ["user_id", "signup_source"],
    "user_logout": ["user_id"],
    "feature_viewed": ["user_id", "feature_name"],
    "feature_created": ["user_id", "feature_name"],
    "feature_shared": ["user_id", "feature_name"],
    "feature_deleted": ["user_id", "feature_name"],
    "search_executed": ["user_id", "num_conditions", "result_count"],
    "search_saved": ["user_id", "num_conditions"],
    "valuation_compared": ["user_id", "player_id"],
    "transfer_candidate_viewed": ["user_id", "template_name"],
    "opportunity_viewed": ["user_id", "opportunity_type", "player_id"],
    "subscription_created": ["user_id", "subscription_tier"],
    "subscription_canceled": ["user_id", "subscription_duration_days"],
    "subscription_renewed": ["user_id", "subscription_tier"],
    "upgrade_attempted": ["user_id", "triggering_feature"],
    "upgrade_completed": ["user_id", "subscription_tier"],
    "org_created": ["user_id", "org_name"],
    "org_member_invited": ["user_id", "org_id", "role_invited"],
    "org_member_joined": ["user_id", "org_id", "role"],
    "error_occurred": ["error_type", "error_message"],
    "tactical_analysis_viewed": ["user_id", "analysis_type", "match_id"],
    "dashboard_viewed": ["user_id"],
    "widget_interacted": ["user_id", "widget_name", "action"],
    "report_generated": ["user_id", "player_id"],
    "report_exported": ["user_id", "report_id", "export_format"],
    "alert_triggered": ["user_id", "watch_id", "alert_type"],
    "alert_dismissed": ["user_id", "alert_id"],
}


def track_event(
    db: Session,
    *,
    event_name: str,
    properties: dict,
    user_id: int | None = None,
    session_id: str | None = None,
) -> AnalyticsEvent:
    """Record a validated analytics event.

    Raises ValueError if the event is unknown or missing required properties.
    This is intentional — unknown events must be explicitly registered, never
    silently accepted (Constitution §6.5: never silently swallow errors).
    """
    if event_name not in REQUIRED_PROPERTIES:
        raise ValueError(
            f"Unknown event '{event_name}'.  Register it in "
            "app/analytics/events.py REQUIRED_PROPERTIES first."
        )

    required = REQUIRED_PROPERTIES[event_name]
    missing = [k for k in required if k not in properties]
    if missing:
        raise ValueError(
            f"Event '{event_name}' missing required properties: {missing}"
        )

    event = AnalyticsEvent(
        user_id=user_id,
        session_id=session_id,
        event_name=event_name,
        event_properties=properties,
    )
    db.add(event)

    # Session management: update existing or create new (Part A3).
    if session_id and user_id:
        _upsert_session(db, session_id, user_id, event_name)

    db.flush()
    return event


def _upsert_session(
    db: Session,
    session_id: str,
    user_id: int,
    event_name: str,
) -> None:
    """Create or update an analytics session.

    Sessions end after SESSION_TIMEOUT_MINUTES of inactivity.
    """
    session = (
        db.query(AnalyticsSession)
        .filter(AnalyticsSession.session_id == session_id)
        .first()
    )

    now = datetime.now(timezone.utc)

    if session is None:
        session = AnalyticsSession(
            session_id=session_id,
            user_id=user_id,
            started_at=now,
            event_count=1,
            events_json={"events": [event_name]},
        )
        db.add(session)
    else:
        # Check if session has timed out.
        if (
            session.ended_at is not None
            and (now - session.ended_at) > timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        ):
            # Start a new session with the same ID prefix.
            session.ended_at = session.ended_at
            session = AnalyticsSession(
                session_id=f"{session_id}-{int(now.timestamp())}",
                user_id=user_id,
                started_at=now,
                event_count=1,
                events_json={"events": [event_name]},
            )
            db.add(session)
        else:
            # Extend existing session.
            session.event_count += 1
            events = session.events_json.get("events", []) if session.events_json else []
            events.append(event_name)
            session.events_json = {"events": events[-100:]}  # keep last 100
            session.ended_at = now
            # Handle both naive and aware datetimes from SQLite vs PostgreSQL
            started = session.started_at
            now_naive = now.replace(tzinfo=None)
            if started.tzinfo is None:
                session.duration_seconds = int((now_naive - started).total_seconds())
            else:
                session.duration_seconds = int((now - started).total_seconds())


def flush_event(db: Session, event: AnalyticsEvent) -> None:
    """Commit an event to the database.

    Call this after track_event to persist.  Keeping flush and commit
    separate allows batching multiple events in a single transaction.
    """
    db.commit()
