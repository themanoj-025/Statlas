"""Alert delivery (Phase 10 — Part D).

Two non-negotiable quality bars (docs/product/alert-trigger-definitions.md §5):

1. PREFERENCE COMPLIANCE: delivery NEVER sends an email for a trigger type or
   channel the user has opted out of — email_enabled=False, a disabled alert
   type, or digest-only frequency all suppress email (in-app alerts are always
   recorded). This is tested as rigorously as an authorization check.
2. ANTI-NOISE: digest-frequency users get ONE batched email per period, never
   one email per alert. `deliver_pending` handles immediate delivery;
   `send_digests(frequency)` is called by the orchestrator for daily/weekly.

Delivery failure never silently drops an alert: emails that fail are logged
and the alert stays undelivered (delivered_at NULL) so a later run retries.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import NotificationPreferences, User, Watch, WatchAlert
from app.notifications.email import (
    EmailDeliveryError,
    NotConfiguredError,
    _email_for,
    alert_email_content,
    digest_email_content,
    get_sender,
)
from app.queries.watch_queries import ALERT_TYPES

logger = logging.getLogger(__name__)

DIGEST_FREQUENCIES = ("immediate", "daily_digest", "weekly_digest")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prefs(db: Session, user_id: int) -> NotificationPreferences | None:
    return db.query(NotificationPreferences).filter_by(user_id=user_id).first()


def _token_for(db: Session, user_id: int) -> str:
    """The user's stored unsubscribe token — minted on first email so the
    signed link in every email matches what the unsubscribe endpoint checks."""
    import secrets

    prefs = _prefs(db, user_id)
    if prefs is not None and prefs.unsubscribe_token:
        return prefs.unsubscribe_token
    token = secrets.token_urlsafe(32)
    if prefs is None:
        prefs = NotificationPreferences(
            user_id=user_id,
            alert_type_preferences={t: True for t in ALERT_TYPES},
        )
        db.add(prefs)
    prefs.unsubscribe_token = token
    db.flush()
    return token


def _user_email(db: Session, user_id: int) -> str | None:
    user = db.get(User, user_id)
    return user.email if user else None


def _alert_deliverable(alert: WatchAlert) -> bool:
    """An alert is ready for email when it was never delivered (delivered_at
    NULL) and not dismissed. read_at does not suppress email — an email may
    have been opened before the in-app alert was read."""
    return alert.delivered_at is None and not alert.dismissed


def _email_for_alert(db: Session, alert: WatchAlert) -> tuple[str, str] | None:
    """(subject, html) for one alert, using real detail data."""
    return alert_email_content(alert.alert_type, alert.detail or {})


def deliver_immediate(
    db: Session, *, sender: Any | None = None, now: datetime | None = None
) -> dict[str, int]:
    """Deliver immediate-mode alerts that haven't been emailed yet.

    Preference compliance: email is only attempted when the user has email
    enabled AND the alert's type is enabled AND their digest frequency is
    `immediate`. In-app alerts are unaffected.

    Returns {delivered, skipped_opt_out, skipped_no_email, failed}.
    """
    sender = sender or get_sender()
    now = now or _now()
    stats = {"delivered": 0, "skipped_opt_out": 0, "skipped_no_email": 0, "failed": 0}

    pending = (
        db.query(WatchAlert, Watch, NotificationPreferences, User)
        .join(Watch, WatchAlert.watch_id == Watch.id)
        .outerjoin(
            NotificationPreferences, NotificationPreferences.user_id == Watch.user_id
        )
        .outerjoin(User, User.id == Watch.user_id)
        .filter(WatchAlert.delivered_at.is_(None), WatchAlert.dismissed.is_(False))
        .order_by(WatchAlert.triggered_at.asc())
        .all()
    )

    for alert, watch, prefs, user in pending:
        if prefs is None:
            # No preferences row yet = documented defaults (email on, all
            # types on, immediate). Column defaults only apply on INSERT, so
            # an in-memory row would read None — use explicit defaults.
            email_on, type_on, digest_ok = True, True, True
        else:
            email_on = prefs.email_enabled
            type_on = bool(
                (prefs.alert_type_preferences or {}).get(alert.alert_type, True)
            )
            digest_ok = prefs.digest_frequency == "immediate"
        email = user.email if user else None

        if not (email_on and type_on and digest_ok):
            stats["skipped_opt_out"] += 1
            continue
        if not email:
            stats["skipped_no_email"] += 1
            continue

        content = _email_for_alert(db, alert)
        if content is None:
            stats["failed"] += 1
            continue
        subject, html = content
        token = _token_for(db, watch.user_id)
        try:
            message = _email_for(
                to=email,
                subject=subject,
                body_html=html,
                body_text=f"{subject}\n\nView on Statlas and manage preferences.",
                user_id=watch.user_id,
                unsubscribe_token=token,
            )
            sender(message)
            alert.delivered_at = now
            stats["delivered"] += 1
        except NotConfiguredError:
            # Honest no-config state: in-app alerts remain; email waits for a
            # configured key. Not a failure of the alert itself.
            logger.info("email not configured — alert %s stays in-app only", alert.id)
            break
        except EmailDeliveryError as exc:
            logger.warning("delivery failed for alert %s: %s", alert.id, exc)
            stats["failed"] += 1

    db.commit()
    return stats


def send_digests(
    db: Session,
    frequency: str,
    *,
    sender: Any | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Batch each digest-frequency user's undelivered alerts into ONE email.

    Called by the orchestrator for daily_digest/weekly_digest. A digest email
    covers every alert the user hasn't received yet (since the last delivery),
    so users on digest mode never get per-alert emails.

    Returns {digests_sent, alerts_included, users_with_no_alerts}.
    """
    sender = sender or get_sender()
    now = now or _now()
    stats = {"digests_sent": 0, "alerts_included": 0, "users_with_no_alerts": 0}

    if frequency not in ("daily_digest", "weekly_digest"):
        raise ValueError(
            f"send_digests expects daily_digest or weekly_digest, got {frequency}"
        )

    # Users on this digest frequency with at least one undelivered alert.
    rows = (
        db.query(User, NotificationPreferences, WatchAlert, Watch)
        .join(NotificationPreferences, NotificationPreferences.user_id == User.id)
        .join(Watch, Watch.user_id == User.id)
        .join(WatchAlert, WatchAlert.watch_id == Watch.id)
        .filter(
            NotificationPreferences.digest_frequency == frequency,
            NotificationPreferences.email_enabled.is_(True),
            WatchAlert.delivered_at.is_(None),
            WatchAlert.dismissed.is_(False),
        )
        .order_by(WatchAlert.triggered_at.asc())
        .all()
    )
    by_user: dict[int, list[tuple[WatchAlert, dict[str, Any]]]] = defaultdict(list)
    for user, prefs, alert, watch in rows:
        if not bool((prefs.alert_type_preferences or {}).get(alert.alert_type, True)):
            continue  # opted out of this trigger type — skip, not delivered
        by_user[user.id].append((alert, alert.detail or {}))

    for user_id, alerts in by_user.items():
        user = db.get(User, user_id)
        if user is None or not user.email:
            stats["users_with_no_alerts"] += 0
            continue
        subject, html = digest_email_content(
            user.email, [(a.alert_type, d) for a, d in alerts], frequency
        )
        token = _token_for(db, user_id)
        try:
            message = _email_for(
                to=user.email,
                subject=subject,
                body_html=html,
                body_text=f"{subject}\n\nView on Statlas and manage preferences.",
                user_id=user_id,
                unsubscribe_token=token,
            )
            sender(message)
            for alert, _detail in alerts:
                alert.delivered_at = now
            stats["digests_sent"] += 1
            stats["alerts_included"] += len(alerts)
        except NotConfiguredError:
            logger.info("email not configured — digest skipped for user %s", user_id)
            break
        except EmailDeliveryError as exc:
            logger.warning("digest delivery failed for user %s: %s", user_id, exc)

    db.commit()
    return stats


def run_due_digests(
    db: Session, *, sender: Any | None = None, now: datetime | None = None
) -> dict[str, int]:
    """Orchestrator entry: send whichever digests are due (daily every day,
    weekly every Monday). Idempotent — already-delivered alerts are skipped by
    the delivered_at filter."""
    now = now or _now()
    results = {"daily_digest": 0, "weekly_digest": 0}
    # Daily digests are always due; weekly on Mondays (UTC).
    results["daily_digest"] = send_digests(db, "daily_digest", sender=sender, now=now)[
        "digests_sent"
    ]
    if now.weekday() == 0:  # Monday
        results["weekly_digest"] = send_digests(
            db, "weekly_digest", sender=sender, now=now
        )["digests_sent"]
    return results
