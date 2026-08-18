"""Phase 13 — personal dashboard API routes.

Every authenticated route requires a signed-in session (401 otherwise).
This module is a thin HTTP layer — all business logic lives in
queries/dashboard_queries.py and activity.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import auth
from app.activity import log_activity
from app.config import get_settings
from app.db import session_scope
from app.models import User
from app.queries import dashboard_queries as dq

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _require_user(request: Request) -> User:
    with session_scope() as db:
        user = auth.user_from_session(
            db, request.cookies.get(get_settings().session_cookie_name)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to view your dashboard.")
        return user


# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------


class ActivityRequest(BaseModel):
    entity_type: str  # player | team | search | shortlist | report | watch
    entity_id: int
    action_type: str  # viewed | created | edited | deleted | shared | run


@router.post("/activity")
def log_user_activity(request: Request, body: ActivityRequest):
    """Log a user activity event (with 60s deduplication).

    Called from the frontend on page load (player/team profile views)
    and on user-initiated actions (create, edit, etc.).
    """
    user = _require_user(request)

    if body.entity_type not in ("player", "team", "search", "shortlist", "report", "watch"):
        raise HTTPException(status_code=400, detail=f"Invalid entity_type: {body.entity_type}")
    if body.action_type not in ("viewed", "created", "edited", "deleted", "shared", "run"):
        raise HTTPException(status_code=400, detail=f"Invalid action_type: {body.action_type}")

    with session_scope() as db:
        logged = log_activity(
            db,
            user_id=user.id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            action_type=body.action_type,
        )
    return {"logged": logged}


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------


@router.get("/summary")
def dashboard_summary(request: Request):
    """Aggregate counts for workspace shortcuts + recent activity + trending
    + recommended — a single round-trip for the dashboard page.
    """
    user = _require_user(request)

    with session_scope() as db:
        recent = dq.get_recent_activity(db, user.id)
        workspace = dq.get_workspace_summary(db, user.id)
        trending = dq.get_trending_players(db, user.id)
        recommended = dq.get_recommended_players(db, user.id)
        saved = dq.get_saved_players(db, user.id)

    return {
        "recent_activity": recent,
        "workspace": workspace,
        "trending_players": trending,
        "recommended_players": recommended,
        "saved_players": saved,
    }


# ---------------------------------------------------------------------------
# Saved players
# ---------------------------------------------------------------------------


class SavePlayerRequest(BaseModel):
    player_id: int
    category: str | None = None


@router.post("/saved-players")
def save_player_endpoint(request: Request, body: SavePlayerRequest):
    """Bookmark a player (lightweight save, distinct from shortlists)."""
    user = _require_user(request)
    with session_scope() as db:
        entry = dq.save_player(db, user.id, body.player_id, body.category)
        return {"saved": True, "player_id": entry.player_id}


@router.delete("/saved-players/{player_id}")
def unsave_player_endpoint(request: Request, player_id: int):
    """Remove a player from the user's saved list."""
    user = _require_user(request)
    with session_scope() as db:
        removed = dq.unsave_player(db, user.id, player_id)
        return {"removed": removed}


# ---------------------------------------------------------------------------
# Dismiss recommendation
# ---------------------------------------------------------------------------


class DismissRequest(BaseModel):
    player_id: int


@router.post("/dismiss-recommendation")
def dismiss_recommendation_endpoint(request: Request, body: DismissRequest):
    """Dismiss a recommended player (won't reappear for 30 days)."""
    user = _require_user(request)
    with session_scope() as db:
        dq.dismiss_recommendation(db, user.id, body.player_id)
        return {"dismissed": True}
