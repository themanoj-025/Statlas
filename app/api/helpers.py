"""Statlas API helpers -- session management and activity logging."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request

from app import auth
from app.config import get_settings
from app.db import session_scope

logger = logging.getLogger(__name__)


def _with_session(fn: Callable[[Any], Any], *args: Any, **kwargs: Any) -> Any:
    """Run a query function against a fresh session (closed on return)."""
    with session_scope() as db:
        return fn(db, *args, **kwargs)


def _log_player_view(request: Request, player_id: int) -> None:
    """Log a player view activity event (best-effort, never breaks response)."""
    try:
        from app.activity import log_activity

        with session_scope() as db:
            user = auth.user_from_session(
                db, request.cookies.get(get_settings().session_cookie_name)
            )
            if user is not None:
                log_activity(
                    db,
                    user_id=user.id,
                    entity_type="player",
                    entity_id=player_id,
                    action_type="viewed",
                )
    except (OSError, ValueError) as exc:
        logger.debug("Activity logging failed for player view: %s", exc)
