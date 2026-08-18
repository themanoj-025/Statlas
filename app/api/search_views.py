"""Phase 8 — structured search API routes.

Execution is POST so the full query definition travels in the body (a URL
query string would be unwieldy and error-prone). Presets are public; saved
searches and history are session-authenticated with the Phase 7 ownership
pattern (404 for foreign/missing ids, never an existence-leaking 403).

Domain error mapping:
- InvalidQuery          -> 400 (specific grammar/validation message)
- SearchNotFound        -> 404 (missing OR foreign)
- SearchLimitExceeded   -> 403 (honest free-tier upsell)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app import auth
from app.api.deps import require_user, session_token
from app.config import get_settings
from app.db import session_scope
from app.models import User
from app.queries import structured_search as ss

router = APIRouter(prefix="/api/v1/search", tags=["search"])


# _require_user consolidated into app/api/deps.py
_require_user = require_user
_session_token = session_token


def _optional_user(request: Request) -> User | None:
    with session_scope() as db:
        return auth.user_from_session(
            db, request.cookies.get(get_settings().session_cookie_name)
        )


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ss.SearchNotFound,)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ss.SearchLimitExceeded):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (ss.InvalidQuery, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Something went wrong.")


# ---------------------------------------------------------------------------
# Bodies
# ---------------------------------------------------------------------------


class QueryDefinitionBody(BaseModel):
    query_definition: dict


class ExecuteBody(QueryDefinitionBody):
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = "index"
    sort_dir: str | None = None
    log_history: bool = True


class RunBody(BaseModel):
    """Re-running a SAVED search (or history entry) needs no query definition
    — the stored one is re-executed server-side."""

    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = "index"
    sort_dir: str | None = None


class SaveSearchBody(QueryDefinitionBody):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/execute")
def execute(body: ExecuteBody, request: Request):
    user = _optional_user(request)
    with session_scope() as db:
        try:
            return ss.execute_structured_query(
                db,
                body.query_definition,
                user_id=user.id if user else None,
                log_history=body.log_history,
                limit=body.limit,
                offset=body.offset,
                sort_by=body.sort_by,
                sort_dir=body.sort_dir,
            )
        except Exception as exc:  # noqa: BLE001 — domain mapping below
            raise _map_error(exc)


@router.get("/presets")
def presets():
    return {"presets": ss.list_presets()}


@router.get("/saved")
def saved_searches(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        return {"searches": ss.list_saved_searches(db, user.id)}


@router.post("/saved", status_code=201)
def save_search(body: SaveSearchBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return ss.save_search(
                db, user.id, body.name, body.query_definition, description=body.description
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/saved/{search_id}/run")
def run_saved(search_id: int, body: RunBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return ss.run_saved_search(
                db,
                user.id,
                search_id,
                limit=body.limit,
                offset=body.offset,
                sort_by=body.sort_by,
                sort_dir=body.sort_dir,
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.delete("/saved/{search_id}")
def delete_saved(search_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            ss.delete_saved_search(db, user.id, search_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.get("/history")
def history(request: Request, limit: int = Query(20, ge=1, le=50)):
    user = _require_user(request)
    with session_scope() as db:
        return {"entries": ss.get_search_history(db, user.id, limit=limit)}


@router.post("/history/{history_id}/rerun")
def rerun_history(history_id: int, body: RunBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return ss.rerun_history_entry(
                db,
                user.id,
                history_id,
                limit=body.limit,
                offset=body.offset,
                sort_by=body.sort_by,
                sort_dir=body.sort_dir,
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)
