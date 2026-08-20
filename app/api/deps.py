"""Shared API dependencies — eliminates duplicate _require_user across views.

Every authenticated route module previously defined its own identical copy of
this function.  Centralising it here means a single source of truth for the
session-resolution + 401-raise pattern, consistent with the Constitution's
bias against silent duplication (§4 code quality).

P1.2 fix: require_user now reuses the session from the FastAPI dependency
injection graph instead of opening a second DB session.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import auth
from app.config import get_settings
from app.db import session_scope
from app.models import User


def session_token(request: Request) -> str | None:
    """Extract the session cookie value from a request."""
    return request.cookies.get(get_settings().session_cookie_name)


def require_user(
    request: Request,
    db: Session = Depends(lambda: session_scope()),
) -> User:
    """Resolve the current session to a User, or raise 401.

    Reuses the injected ``db`` session so views that depend on both
    ``require_user`` and ``get_session`` share one connection.

    Used by every authenticated view module (billing, workspace, search,
    reports, watch, dashboard, public API).
    """
    user = auth.user_from_session(db, session_token(request))
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return user
