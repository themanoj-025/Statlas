"""Shared API dependencies — eliminates duplicate _require_user across views.

Every authenticated route module previously defined its own identical copy of
this function.  Centralising it here means a single source of truth for the
session-resolution + 401-raise pattern, consistent with the Constitution's
bias against silent duplication (§4 code quality).

NOTE: require_user opens its own session scope because some callers invoke it
as a plain function (e.g. _require_user(request) in billing_views) rather than
through FastAPI's dependency-injection graph.  A future refactor could convert
every caller to use Depends(require_user) and then share the session.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app import auth
from app.config import get_settings
from app.db import session_scope
from app.models import User


def session_token(request: Request) -> str | None:
    """Extract the session cookie value from a request."""
    return request.cookies.get(get_settings().session_cookie_name)


def require_user(request: Request) -> User:
    """Resolve the current session to a User, or raise 401.

    Used by every authenticated view module (billing, workspace, search,
    reports, watch, dashboard, public API).

    NOTE: The returned User is detached from its session scope. Callers that
    need the User within a different session_scope() must re-fetch via
    db.get(User, user.id) to avoid DetachedInstanceError on lazy-loaded
    relationships.
    """
    with session_scope() as db:
        user = auth.user_from_session(db, session_token(request))
        if user is None:
            raise HTTPException(status_code=401, detail="Not signed in.")
        return user
