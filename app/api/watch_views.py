"""Phase 10 — watchlist & alerts API routes.

Every route requires a signed-in session (401 otherwise) EXCEPT the
one-click unsubscribe endpoint (it is clicked from email with a signed token
and must work without a session). All ownership, cap, and preference logic
lives in queries/watch_queries; this module maps domain errors to HTTP
statuses:

- WatchNotFound / EntityNotFound -> 404 (existence never leaks)
- WatchLimitExceeded             -> 403 (honest upsell copy)
- ValueError                     -> 400 (validation)
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import auth
from app.config import get_settings
from app.db import session_scope
from app.models import NotificationPreferences, User
from app.queries import watch_queries as wq

router = APIRouter(prefix="/api/v1/watch", tags=["watchlist"])


def _require_user(request: Request) -> User:
    with session_scope() as db:
        user = auth.user_from_session(
            db, request.cookies.get(get_settings().session_cookie_name)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to use your watchlist.")
        return user


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (wq.WatchNotFound, wq.EntityNotFound)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, wq.WatchLimitExceeded):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Something went wrong.")


# ---------------------------------------------------------------------------
# Bodies
# ---------------------------------------------------------------------------


class FollowBody(BaseModel):
    entity_type: str = Field(pattern="^(player|team)$")
    entity_id: int
    followed_metrics: list[str] | None = Field(default=None, max_length=30)


class PreferencesBody(BaseModel):
    email_enabled: bool | None = None
    alert_type_preferences: dict[str, bool] | None = None
    digest_frequency: str | None = Field(default=None, max_length=16)


# ---------------------------------------------------------------------------
# Watches
# ---------------------------------------------------------------------------


@router.get("")
def my_watches(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        return {"watches": wq.list_watches(db, user.id)}


@router.post("", status_code=201)
def follow(body: FollowBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.follow_entity(
                db,
                user.id,
                body.entity_type,
                body.entity_id,
                followed_metrics=body.followed_metrics,
            )
        except Exception as exc:  # noqa: BLE001 — domain mapping below
            raise _map_error(exc)


@router.post("/{watch_id}/unfollow")
def unfollow(watch_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.unfollow_entity(db, user.id, watch_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


@router.get("/alerts")
def alerts(
    request: Request,
    include_read: bool = Query(False),
    include_dismissed: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
):
    user = _require_user(request)
    with session_scope() as db:
        return {
            "alerts": wq.list_alerts(
                db,
                user.id,
                include_read=include_read,
                include_dismissed=include_dismissed,
                limit=limit,
            )
        }


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.get_alert(db, user.id, alert_id)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/alerts/{alert_id}/read")
def mark_read(alert_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.mark_alert_read(db, user.id, alert_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/alerts/{alert_id}/dismiss")
def dismiss(alert_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.dismiss_alert(db, user.id, alert_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get("/preferences")
def preferences(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        return wq.get_preferences(db, user.id)


@router.put("/preferences")
def update_preferences(body: PreferencesBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.update_preferences(
                db,
                user.id,
                email_enabled=body.email_enabled,
                alert_type_preferences=body.alert_type_preferences,
                digest_frequency=body.digest_frequency,
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/preferences/rotate-token")
def rotate_token(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        return wq.rotate_unsubscribe_token(db, user.id)


# ---------------------------------------------------------------------------
# Public — one-click unsubscribe (sessionless, signed token in the email)
# ---------------------------------------------------------------------------


def _check_sig(user_id: int, token: str, sig: str) -> bool:
    settings = get_settings()
    secret = settings.alert_signing_secret or ""
    expected = hmac.new(
        secret.encode(), f"{user_id}:{token}".encode(), hashlib.sha256
    ).hexdigest()[:32]
    return hmac.compare_digest(expected, sig)


@router.get("/unsubscribe")
def unsubscribe(
    user: int,
    token: str = Query(..., max_length=64),
    sig: str = Query(..., max_length=64),
):
    """One-click unsubscribe from email. Invalid/expired signatures are
    rejected with an honest message rather than silently doing nothing."""
    if not _check_sig(user, token, sig):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "This unsubscribe link is invalid or expired. Sign in and "
                "open Settings to manage your notification preferences."
            },
        )
    with session_scope() as db:
        prefs = db.query(NotificationPreferences).filter_by(user_id=user).first()
        if prefs is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "No notification preferences found for this account."},
            )
        if prefs.unsubscribe_token != token:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "This unsubscribe link has already been used or replaced. "
                    "Sign in and open Settings to manage your preferences."
                },
            )
        prefs.email_enabled = False
        db.commit()
        return JSONResponse(
            status_code=200,
            content={
                "detail": "You've been unsubscribed from Statlas alert emails. "
                "You can re-enable them anytime from your watchlist settings.",
                "preferences_url": "/watchlist/settings",
            },
        )
