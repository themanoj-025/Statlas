"""Phase 4 — Part C: public API.

- Key management (dashboard): create (one-time reveal), list (prefixes only),
  revoke, rotate — all owner-scoped to the signed-in user.
- Rate-limited read endpoints under /api/v1/public/... authenticated via
  `Authorization: Bearer <key>`, returning X-RateLimit-* headers per
  pricing.json. A simple in-memory sliding window per key (documented in the
  security review; Redis is the production upgrade path).
- 4xx responses are specific and actionable; genuine failures raise (5xx),
  logged at the layer above.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app import api_keys
from app.api.deps import require_user, session_token
from app.db import session_scope
from app.models import User
from app.queries import leaderboard_queries, player_queries

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["public-api"])

# Rate limiter — uses Redis when available, falls back to in-memory.
_WINDOW = 60


# ---------------------------------------------------------------------------
# Key management (session-authenticated dashboard)
# ---------------------------------------------------------------------------


class KeyCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class KeyRotateBody(BaseModel):
    name: str | None = Field(default=None, max_length=128)


# _require_user consolidated into app/api/deps.py
_require_user = require_user
_session_token = session_token


@router.post("/keys", status_code=201)
def create_api_key(body: KeyCreateBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        result = api_keys.generate_api_key(db, user, body.name)
    return result  # raw key — one-time reveal


@router.get("/keys")
def list_keys(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        return {"keys": api_keys.list_api_keys(db, user.id)}


@router.delete("/keys/{key_id}")
def revoke_key(key_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        ok = api_keys.revoke_api_key(db, user.id, key_id)
    if not ok:
        raise HTTPException(
            status_code=404, detail="No API key with that id for this account."
        )
    return {"ok": True}


@router.post("/keys/{key_id}/rotate")
def rotate_key(key_id: int, body: KeyRotateBody | None = None, request: Request = None):
    user = _require_user(request)
    with session_scope() as db:
        result = api_keys.rotate_api_key(
            db, user, key_id, (body.name if body else None)
        )
    if result is None:
        raise HTTPException(
            status_code=404, detail="No API key with that id for this account."
        )
    return result  # new raw key — one-time reveal


# ---------------------------------------------------------------------------
# Rate-limited public read endpoints (bearer API key)
# ---------------------------------------------------------------------------


def _check_rate_limit(key_hash: str, plan: str) -> dict:
    from app.rate_limiting import get_rate_limiter

    limits = api_keys.api_rate_limit_for_plan(plan)
    rpm = limits["per_minute"]
    if rpm <= 0:
        raise HTTPException(
            status_code=403,
            detail="The public API is not included in your current plan. Upgrade to the API Business tier to use it.",
        )
    limiter = get_rate_limiter()
    if limiter.is_limited(f"apikey:{key_hash}", max_attempts=rpm, window_seconds=_WINDOW):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded — {rpm} requests/minute allowed on your plan. Retry shortly.",
        )
    remaining = limiter.get_remaining(f"apikey:{key_hash}", max_attempts=rpm)
    return {"remaining": remaining, "limit": rpm}


def api_key_dependency(request: Request) -> tuple[User, str]:
    auth_header = request.headers.get("authorization", "")
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    with session_scope() as db:
        resolved = api_keys.authenticate_api_key(db, token)
        if resolved is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or revoked API key. Generate one in your account dashboard.",
            )
        user, plan = resolved
        limit_info = _check_rate_limit(token, plan)
    request.state.rate_limit = limit_info
    return user, plan


def _public_headers(limit_info: dict) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(limit_info["limit"]),
        "X-RateLimit-Remaining": str(limit_info["remaining"]),
        "X-RateLimit-Window": f"{_WINDOW}s",
    }


def _run(fn: Any, *args: Any, **kwargs: Any) -> dict:
    with session_scope() as db:
        return fn(db, *args, **kwargs)


@router.get("/public/players/search")
def public_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=64),
    _: tuple = Depends(api_key_dependency),
):
    results = _run(player_queries.search_players, q, 10)
    return {"results": results}


@router.get("/public/players/{player_id}/percentiles")
def public_percentiles(
    request: Request, player_id: int, _: tuple = Depends(api_key_dependency)
):
    data = _run(player_queries.get_player_percentiles, player_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail="No published percentile data for that player."
        )
    profile = _run(player_queries.get_player_profile, player_id)
    return {"player": profile, "percentiles": data}


@router.get("/public/leaderboard")
def public_leaderboard(
    request: Request,
    metric: str = Query(..., min_length=1, max_length=64),
    league: str | None = None,
    position: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    _: tuple = Depends(api_key_dependency),
):
    if not league:
        raise HTTPException(
            status_code=400,
            detail="The leaderboard endpoint requires a league slug (e.g. league=premier-league).",
        )
    rows = _run(
        leaderboard_queries.get_leaderboard,
        league_slug=league,
        position_group=position,
        metric=metric,
        season=None,
        limit=limit,
    )
    return {"metric": metric, "league": league, "rows": rows[:limit]}


def apply_rate_limit_headers(response, request: Request) -> None:
    """Called from app-level middleware (main.py) — router middleware does not
    reliably attach in all FastAPI versions."""
    limit_info = getattr(request.state, "rate_limit", None)
    if limit_info is not None:
        for k, v in _public_headers(limit_info).items():
            response.headers[k] = v
