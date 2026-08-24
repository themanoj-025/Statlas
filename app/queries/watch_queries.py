"""Phase 10 — Watchlist & alerts query layer.

The single service layer behind every watch API route. Rules enforced here
(all documented in docs/product/alert-trigger-definitions.md):

- OWNERSHIP: every function takes the requesting user_id and verifies it on
  every read/write. A missing OR foreign watch/alert raises WatchNotFound
  (mapped to HTTP 404 by the API) — never a 403 that would leak existence.
- UNIQUE (user_id, entity_type, entity_id): a player/team can be followed
  once; following again is a no-op returning the existing watch.
- TIER CAPS: Free = 10 watched entities (pricing.json `watches_max`).
  Exceeding the cap raises WatchLimitExceeded (403 + honest upsell copy).
- PREFERENCES: email_enabled + alert_type_preferences are honored at
  delivery time (app/watch/delivery.py); this layer only reads/writes them.
- ALERTS: reads are scoped to the watch owner; an alert's `detail` is real
  snapshot data written by detection (never fabricated here).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth import effective_plan
from app.config import plan_limits
from app.models import (
    League,
    NotificationPreferences,
    Player,
    Team,
    Watch,
    WatchAlert,
)
from app.queries.player_queries import get_player_slug, slugify_name

ALERT_TYPES = (
    "percentile_movement",
    "club_change",
    "new_season_data",
    "data_coverage_change",
)
DIGEST_FREQUENCIES = ("immediate", "daily_digest", "weekly_digest")


class WatchNotFound(ValueError):
    """Missing OR not owned — mapped to 404 (existence must not leak)."""


class EntityNotFound(ValueError):
    """The followed player/team id does not exist."""


class WatchLimitExceeded(ValueError):
    """Free-tier cap reached — the message is an honest, specific upsell."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------


def _owned_watch(db: Session, user_id: int, watch_id: int) -> Watch:
    watch = (
        db.query(Watch).filter(Watch.id == watch_id, Watch.user_id == user_id).first()
    )
    if watch is None:
        raise WatchNotFound(f"watch {watch_id} not found")
    return watch


def _entity_slug(db: Session, entity_type: str, entity_id: int) -> str | None:
    """The canonical profile slug for an entity (deep links from alerts)."""
    if entity_type == "player":
        if db.get(Player, entity_id) is None:
            return None
        try:
            return get_player_slug(db, entity_id)
        except (OSError, ValueError):  # slug resolution must never break an alert read
            return None
    team = db.get(Team, entity_id)
    if team is None:
        return None
    return slugify_name(team.name)


def _entity_name(
    db: Session, entity_type: str, entity_id: int
) -> tuple[str, str | None]:
    """(name, slug) for an entity — used for links and alert display."""
    if entity_type == "player":
        player = db.get(Player, entity_id)
        if player is None:
            raise EntityNotFound(f"No player with id {entity_id} exists.")
        return player.canonical_name, _entity_slug(db, entity_type, entity_id)
    team = db.get(Team, entity_id)
    if team is None:
        raise EntityNotFound(f"No team with id {entity_id} exists.")
    return team.name, _entity_slug(db, entity_type, entity_id)


# ---------------------------------------------------------------------------
# Watches CRUD
# ---------------------------------------------------------------------------


def follow_entity(
    db: Session,
    user_id: int,
    entity_type: str,
    entity_id: int,
    followed_metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Follow a player or team. Following an already-followed entity is a
    no-op returning the existing watch (idempotent by the unique constraint).

    `followed_metrics` is the optional per-metric refinement (A4): null/empty
    means broad \"any significant movement\" across the position metric set.
    """
    if entity_type not in ("player", "team"):
        raise ValueError(f"Unknown entity type '{entity_type}' — use player or team.")
    _entity_name(db, entity_type, entity_id)

    # Tier cap (honest upsell, never a generic error).
    plan = effective_plan(db, user_id)
    limits = plan_limits(plan)
    max_watches = limits.get("watches_max")
    if max_watches is not None:
        current = db.query(Watch).filter(Watch.user_id == user_id).count()
        if current >= max_watches:
            raise WatchLimitExceeded(
                f"You've used your {plan} plan's allowance of {max_watches} followed "
                f"players/teams. Upgrade to Pro for unlimited watchlist tracking — "
                f"your existing follows and alert history stay put."
            )

    existing = (
        db.query(Watch)
        .filter(
            Watch.user_id == user_id,
            Watch.entity_type == entity_type,
            Watch.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        return _watch_payload(db, existing)

    watch = Watch(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        followed_metrics=[m for m in (followed_metrics or []) if m] or None,
    )
    db.add(watch)
    db.commit()
    return _watch_payload(db, watch)


def unfollow_entity(db: Session, user_id: int, watch_id: int) -> None:
    """Unfollow. The watch row is deleted but its alert history is retained
    (alerts keep a watch_id FK and are never destroyed — audit bias)."""
    watch = _owned_watch(db, user_id, watch_id)
    db.delete(watch)
    db.commit()


def list_watches(db: Session, user_id: int) -> list[dict[str, Any]]:
    """All the user's watches with entity names and unread-alert counts."""
    watches = (
        db.query(Watch)
        .filter(Watch.user_id == user_id)
        .order_by(Watch.created_at.desc(), Watch.id.desc())
        .all()
    )
    if not watches:
        return []

    watch_ids = [w.id for w in watches]
    unread_rows = (
        db.query(WatchAlert.watch_id, WatchAlert.id)
        .filter(
            WatchAlert.watch_id.in_(watch_ids),
            WatchAlert.read_at.is_(None),
            WatchAlert.dismissed.is_(False),
        )
        .all()
    )
    unread: dict[int, int] = {}
    for watch_id, _alert_id in unread_rows:
        unread[watch_id] = unread.get(watch_id, 0) + 1

    # Player/team identity in two batch queries.
    player_ids = [w.entity_id for w in watches if w.entity_type == "player"]
    team_ids = [w.entity_id for w in watches if w.entity_type == "team"]
    players = (
        {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}
        if player_ids
        else {}
    )
    teams = (
        {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}
        if team_ids
        else {}
    )

    out = []
    for w in watches:
        if w.entity_type == "player":
            player = players.get(w.entity_id)
            name = player.canonical_name if player else f"Player #{w.entity_id}"
            team_name = None
            if player is not None and player.current_team_id is not None:
                team = db.get(Team, player.current_team_id)
                team_name = team.name if team else None
            extra = {
                "team": team_name,
                "position_group": player.position_group if player else None,
            }
        else:
            team = teams.get(w.entity_id)
            name = team.name if team else f"Team #{w.entity_id}"
            league = (
                db.get(League, team.league_id)
                if team is not None and team.league_id is not None
                else None
            )
            extra = {
                "league": league.name if league else None,
                "league_slug": league.slug if league else None,
            }
        out.append(
            {
                "watch_id": w.id,
                "entity_type": w.entity_type,
                "entity_id": w.entity_id,
                "entity_name": name,
                "slug": _entity_slug(db, w.entity_type, w.entity_id),
                "league_slug": extra.pop("league_slug", None),
                "followed_metrics": w.followed_metrics,
                "created_at": w.created_at.isoformat(),
                "unread_alert_count": unread.get(w.id, 0),
                **extra,
            }
        )
    return out


def _watch_payload(db: Session, watch: Watch) -> dict[str, Any]:
    name, slug = _entity_name(db, watch.entity_type, watch.entity_id)
    return {
        "watch_id": watch.id,
        "entity_type": watch.entity_type,
        "entity_id": watch.entity_id,
        "entity_name": name,
        "slug": slug,
        "followed_metrics": watch.followed_metrics,
        "created_at": watch.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


def list_alerts(
    db: Session,
    user_id: int,
    *,
    include_read: bool = False,
    include_dismissed: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """The user's alerts, newest first, scoped through watch ownership.

    `include_read`/`include_dismissed` default to the notification-center view
    (unread, not dismissed); the watchlist page passes include_read=True for
    per-entity recent alerts.
    """
    query = (
        db.query(WatchAlert, Watch)
        .join(Watch, WatchAlert.watch_id == Watch.id)
        .filter(Watch.user_id == user_id)
    )
    if not include_read:
        query = query.filter(WatchAlert.read_at.is_(None))
    if not include_dismissed:
        query = query.filter(WatchAlert.dismissed.is_(False))
    rows = (
        query.order_by(WatchAlert.triggered_at.desc(), WatchAlert.id.desc())
        .limit(limit)
        .all()
    )
    return [_alert_payload(db, alert, watch) for alert, watch in rows]


def get_alert(db: Session, user_id: int, alert_id: int) -> dict[str, Any]:
    """One alert — ownership enforced through its watch (404 on foreign)."""
    row = (
        db.query(WatchAlert, Watch)
        .join(Watch, WatchAlert.watch_id == Watch.id)
        .filter(WatchAlert.id == alert_id, Watch.user_id == user_id)
        .first()
    )
    if row is None:
        raise WatchNotFound(f"alert {alert_id} not found")
    return _alert_payload(db, *row)


def mark_alert_read(db: Session, user_id: int, alert_id: int) -> None:
    alert = _owned_alert(db, user_id, alert_id)
    if alert.read_at is None:
        alert.read_at = _now()
        db.commit()


def dismiss_alert(db: Session, user_id: int, alert_id: int) -> None:
    alert = _owned_alert(db, user_id, alert_id)
    alert.dismissed = True
    db.commit()


def _owned_alert(db: Session, user_id: int, alert_id: int) -> WatchAlert:
    row = (
        db.query(WatchAlert)
        .join(Watch, WatchAlert.watch_id == Watch.id)
        .filter(WatchAlert.id == alert_id, Watch.user_id == user_id)
        .first()
    )
    if row is None:
        raise WatchNotFound(f"alert {alert_id} not found")
    return row


def _alert_payload(db: Session, alert: WatchAlert, watch: Watch) -> dict[str, Any]:
    entity_type = watch.entity_type
    entity_id = watch.entity_id
    if entity_type == "player":
        player = db.get(Player, entity_id)
        name = player.canonical_name if player else f"Player #{entity_id}"
        league_slug = None
    else:
        team = db.get(Team, entity_id)
        name = team.name if team else f"Team #{entity_id}"
        league = (
            db.get(League, team.league_id)
            if team is not None and team.league_id is not None
            else None
        )
        league_slug = league.slug if league else None
    return {
        "alert_id": alert.id,
        "watch_id": watch.id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": name,
        "slug": _entity_slug(db, entity_type, entity_id),
        "league_slug": league_slug,
        "alert_type": alert.alert_type,
        "triggered_at": alert.triggered_at.isoformat(),
        "detail": alert.detail,
        "delivered_at": alert.delivered_at.isoformat() if alert.delivered_at else None,
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
        "dismissed": alert.dismissed,
    }


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------


def get_preferences(db: Session, user_id: int) -> dict[str, Any]:
    """The user's preferences; creates a default row on first access (all
    email on, immediate delivery) so reads are never None-handled."""
    prefs = db.query(NotificationPreferences).filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = NotificationPreferences(
            user_id=user_id,
            alert_type_preferences={t: True for t in ALERT_TYPES},
        )
        db.add(prefs)
        db.commit()
    return {
        "email_enabled": prefs.email_enabled,
        "alert_type_preferences": dict(prefs.alert_type_preferences or {}),
        "digest_frequency": prefs.digest_frequency,
        "updated_at": prefs.updated_at.isoformat(),
    }


def update_preferences(
    db: Session,
    user_id: int,
    *,
    email_enabled: bool | None = None,
    alert_type_preferences: dict[str, bool] | None = None,
    digest_frequency: str | None = None,
) -> dict[str, Any]:
    """Update the user's notification preferences. Unknown alert types or a
    bad digest frequency are rejected with a specific error (never silently
    accepted)."""
    prefs = db.query(NotificationPreferences).filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = NotificationPreferences(
            user_id=user_id,
            alert_type_preferences={t: True for t in ALERT_TYPES},
        )
        db.add(prefs)

    if email_enabled is not None:
        prefs.email_enabled = bool(email_enabled)
    if alert_type_preferences is not None:
        known = set(ALERT_TYPES)
        unknown = set(alert_type_preferences) - known
        if unknown:
            raise ValueError(
                f"Unknown alert type(s): {', '.join(sorted(unknown))} — "
                f"valid types are: {', '.join(ALERT_TYPES)}."
            )
        prefs.alert_type_preferences = {
            t: bool(v) for t, v in alert_type_preferences.items()
        }
    if digest_frequency is not None:
        if digest_frequency not in DIGEST_FREQUENCIES:
            raise ValueError(
                f"Unknown digest frequency '{digest_frequency}' — use "
                f"{', '.join(DIGEST_FREQUENCIES)}."
            )
        prefs.digest_frequency = digest_frequency
    prefs.updated_at = _now()
    db.commit()
    return {
        "email_enabled": prefs.email_enabled,
        "alert_type_preferences": dict(prefs.alert_type_preferences or {}),
        "digest_frequency": prefs.digest_frequency,
        "updated_at": prefs.updated_at.isoformat(),
    }


def _unsubscribe_token(db: Session, user_id: int) -> str:
    """Rotate the user's one-click unsubscribe token (a new token invalidates
    old email links — standard practice)."""
    import secrets

    token = secrets.token_urlsafe(32)
    prefs = db.query(NotificationPreferences).filter_by(user_id=user_id).first()
    if prefs is None:
        prefs = NotificationPreferences(
            user_id=user_id,
            alert_type_preferences={t: True for t in ALERT_TYPES},
        )
        db.add(prefs)
    prefs.unsubscribe_token = token
    db.commit()
    return token


def rotate_unsubscribe_token(db: Session, user_id: int) -> dict[str, str]:
    return {"unsubscribe_token": _unsubscribe_token(db, user_id)}
