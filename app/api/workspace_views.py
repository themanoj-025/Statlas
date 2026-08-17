"""Phase 7 — scouting workspace API routes.

Every route requires a signed-in session (401 otherwise). All ownership,
pipeline-validation, and tier-cap logic lives in queries/workspace_queries;
this module only maps the domain errors to HTTP statuses:

- ShortlistNotFound / PlayerNotFound  -> 404 (existence never leaks)
- InvalidStatusTransition             -> 400 (specific, actionable message)
- DuplicateEntry                      -> 409
- WorkspaceLimitExceeded              -> 403 (honest upsell copy)
- ValueError                          -> 400 (validation)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app import auth
from app.config import get_settings
from app.config import plan_limits as pricing_limits
from app.db import session_scope
from app.models import User
from app.queries import workspace_queries as wq

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])


def _require_user(request: Request) -> User:
    with session_scope() as db:
        user = auth.user_from_session(
            db, request.cookies.get(get_settings().session_cookie_name)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to use your workspace.")
        return user


def _plan_context(db, user_id: int) -> dict:
    return {
        "plan": auth.effective_plan(db, user_id),
        "has_pro": auth.has_pro_access(db, user_id),
        "limits": pricing_limits(auth.effective_plan(db, user_id)),
    }


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (wq.ShortlistNotFound, wq.PlayerNotFound)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, wq.InvalidStatusTransition):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, wq.DuplicateEntry):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, wq.WorkspaceLimitExceeded):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Something went wrong.")


# ---------------------------------------------------------------------------
# Bodies
# ---------------------------------------------------------------------------


class CreateShortlistBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class AddEntryBody(BaseModel):
    player_id: int
    initial_note: str | None = Field(default=None, max_length=2000)


class StatusBody(BaseModel):
    status: str
    reason_note: str | None = Field(default=None, max_length=1000)


class PriorityBody(BaseModel):
    priority: str | None = Field(default=None, max_length=8)


class NoteBody(BaseModel):
    note_text: str = Field(min_length=1, max_length=4000)


class TagBody(BaseModel):
    tag_text: str = Field(min_length=1, max_length=64)


# ---------------------------------------------------------------------------
# Routes — static paths declared BEFORE /{shortlist_id} so they are not
# captured by the path parameter.
# ---------------------------------------------------------------------------


@router.get("")
def workspace_overview(request: Request):
    user = _require_user(request)
    with session_scope() as db:
        shortlists = wq.list_shortlists(db, user.id)
        return {**_plan_context(db, user.id), "shortlists": shortlists}


@router.get("/tag-suggestions")
def tag_suggestions(
    request: Request, prefix: str = Query("", max_length=64), limit: int = Query(10, ge=1, le=25)
):
    user = _require_user(request)
    with session_scope() as db:
        return {"tags": wq.get_user_tag_suggestions(db, user.id, prefix, limit=limit)}


@router.get("/memberships")
def memberships(request: Request, player_id: int):
    user = _require_user(request)
    with session_scope() as db:
        return {"shortlist_ids": wq.get_shortlist_memberships(db, user.id, player_id)}


@router.post("", status_code=201)
def create_shortlist(body: CreateShortlistBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.create_shortlist(
                db, user.id, body.name, description=body.description
            )
        except Exception as exc:  # noqa: BLE001 — domain mapping below
            raise _map_error(exc)


@router.post("/{shortlist_id}/remove")
def remove_shortlist(shortlist_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.delete_shortlist(db, user.id, shortlist_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.get("/{shortlist_id}")
def shortlist_detail(shortlist_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            detail = wq.get_shortlist_detail(db, user.id, shortlist_id)
            return {**detail, **_plan_context(db, user.id)}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/{shortlist_id}/entries", status_code=201)
def add_entry(shortlist_id: int, body: AddEntryBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.add_player_to_shortlist(
                db, user.id, shortlist_id, body.player_id, initial_note=body.initial_note
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/status")
def change_status(entry_id: int, body: StatusBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.update_entry_status(
                db, user.id, entry_id, body.status, reason_note=body.reason_note
            )
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/priority")
def change_priority(entry_id: int, body: PriorityBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.set_entry_priority(db, user.id, entry_id, body.priority)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/notes", status_code=201)
def add_note(entry_id: int, body: NoteBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.add_entry_note(db, user.id, entry_id, body.note_text)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/tags", status_code=201)
def add_tag(entry_id: int, body: TagBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            return wq.add_entry_tag(db, user.id, entry_id, body.tag_text)
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/tags/remove")
def remove_tag(entry_id: int, body: TagBody, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.remove_entry_tag(db, user.id, entry_id, body.tag_text)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)


@router.post("/entries/{entry_id}/remove")
def remove_entry(entry_id: int, request: Request):
    user = _require_user(request)
    with session_scope() as db:
        try:
            wq.remove_entry_by_id(db, user.id, entry_id)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            raise _map_error(exc)
