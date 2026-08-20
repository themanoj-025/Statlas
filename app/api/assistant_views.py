"""Phase 4 — AI assistant API (Part B).

POST /api/v1/assistant/chat — the grounded function-calling assistant.
- Requires a signed-in session (quotas are per-user).
- Returns 503 with an honest "not configured" state when ANTHROPIC_API_KEY
  is unset (never a scripted demo).
- Consumes the per-user quota (hard cap, reset date stated).
- Simple per-user rate limit (Part B4 abuse guard) on top of the quota.
- Response carries `tool_calls` — the show-your-work data the UI renders.
"""

from __future__ import annotations

import logging
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app import assistant, auth
from app.config import get_settings
from app.db import session_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["assistant"])

# Rate limiter: per-user rolling minute window.
# Uses RedisRateLimiter when available, falls back to in-memory.
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_PER_MINUTE = 12  # generous for interactive use; quota is the real gate


class ChatBody(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1, max_length=20)


def _rate_limit(user_id: int) -> None:
    from app.rate_limiting import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter.is_limited(
        f"assistant:{user_id}",
        max_attempts=_RATE_MAX_PER_MINUTE,
        window_seconds=_RATE_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests — the assistant allows {_RATE_MAX_PER_MINUTE} messages per minute. Slow down and try again shortly.",
        )


@router.post("/assistant/chat")
def chat(body: ChatBody, request: Request):
    settings = get_settings()
    if not assistant.assistant_configured():
        raise HTTPException(
            status_code=503,
            detail="The assistant is not configured on this deployment (ANTHROPIC_API_KEY unset).",
        )

    with session_scope() as db:
        user = auth.user_from_session(
            db, request.cookies.get(settings.session_cookie_name)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to use the assistant.")
        _rate_limit(user.id)

        try:
            result = assistant.run_assistant_turn(db, user, body.messages)
        except assistant.QuotaExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail=f"Assistant query quota reached — resets {exc.reset_date}. "
                "Upgrade to Pro for a higher monthly quota.",
            ) from exc

    return result


@router.get("/assistant/quota")
def assistant_quota(request: Request):
    settings = get_settings()
    with session_scope() as db:
        user = auth.user_from_session(
            db, request.cookies.get(settings.session_cookie_name)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to use the assistant.")
        return assistant.get_quota(db, user)
