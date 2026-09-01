"""Phase 16 — Organization API routes.

Multi-tenant endpoints for creating/managing organizations, inviting members,
managing roles, and accessing org settings. Every route requires a signed-in
session. RBAC is enforced via user_has_permission() from org_queries.

Routes:
- POST /api/v1/orgs — create organization
- GET /api/v1/orgs — list user's organizations
- GET /api/v1/orgs/{org_id} — org details
- POST /api/v1/orgs/{org_id}/invite — invite member
- POST /api/v1/orgs/{org_id}/accept-invite — accept invite
- GET /api/v1/orgs/{org_id}/members — list members
- POST /api/v1/orgs/{org_id}/members/{user_id}/role — change role
- POST /api/v1/orgs/{org_id}/members/{user_id}/remove — remove member
- GET /api/v1/orgs/{org_id}/settings — get settings
- PUT /api/v1/orgs/{org_id}/settings — update settings
- GET /api/v1/orgs/{org_id}/audit — audit log
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import require_user
from app.db import session_scope
from app.queries import org_queries as oq

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


def _require_user(request: Request) -> User:
    return require_user(request)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateOrgBody(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    slug: str | None = Field(default=None, max_length=128)
    country: str | None = Field(default=None, max_length=64)


class InviteMemberBody(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    role: str = Field(default="scout", max_length=16)


class AcceptInviteBody(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ChangeRoleBody(BaseModel):
    role: str = Field(min_length=1, max_length=16)


class UpdateSettingsBody(BaseModel):
    data_retention_days: int | None = Field(default=None, ge=7, le=365)
    workspace_name: str | None = Field(default=None, max_length=128)
    enable_audit_logging: bool | None = None
    allow_public_reporting: bool | None = None
    require_2fa: bool | None = None


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
def create_organization(body: CreateOrgBody, request: Request) -> dict[str, Any]:
    """Create a new organization. The creator becomes the owner."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            return oq.create_organization(
                db,
                user.id,
                body.name,
                slug=body.slug,
                country=body.country,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_organizations(request: Request) -> list[dict[str, Any]]:
    """List all organizations the current user belongs to."""
    user = _require_user(request)
    with session_scope() as db:
        return oq.list_user_organizations(db, user.id)


@router.get("/{org_id}")
def get_organization(org_id: int, request: Request) -> dict[str, Any]:
    """Get organization details. Must be a member."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_view"):
            raise HTTPException(status_code=404, detail="Organization not found")
        org = oq.get_organization(db, org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------


@router.post("/{org_id}/invite", status_code=201)
def invite_member(org_id: int, body: InviteMemberBody, request: Request) -> dict[str, str]:
    """Invite a member to the organization."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            return oq.invite_member(db, org_id, user.id, body.email, role=body.role)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{org_id}/accept-invite")
def accept_invite(org_id: int, body: AcceptInviteBody, request: Request) -> dict[str, str]:
    """Accept an org invitation using the invite token."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            return oq.accept_invite(db, body.token, user.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{org_id}/members")
def list_members(org_id: int, request: Request) -> list[dict[str, Any]]:
    """List all members of the organization."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_view"):
            raise HTTPException(status_code=404, detail="Organization not found")
        return oq.list_members(db, org_id)


@router.post("/{org_id}/members/{target_user_id}/role")
def change_member_role(
    org_id: int, target_user_id: int, body: ChangeRoleBody, request: Request
) -> dict[str, str] -> None:
    """Change a member's role. Owner/manager only."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            return oq.change_member_role(db, org_id, user.id, target_user_id, body.role)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{org_id}/members/{target_user_id}/remove")
def remove_member(org_id: int, target_user_id: int, request: Request) -> dict[str, str]:
    """Remove a member from the organization."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            return oq.remove_member(db, org_id, user.id, target_user_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@router.get("/{org_id}/settings")
def get_settings(org_id: int, request: Request) -> dict[str, Any]:
    """Get organization settings. Must be a member."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_view"):
            raise HTTPException(status_code=404, detail="Organization not found")
        settings = oq.get_org_settings(db, org_id)
        if settings is None:
            raise HTTPException(status_code=404, detail="Settings not found")
        return settings


@router.put("/{org_id}/settings")
def update_settings(org_id: int, body: UpdateSettingsBody, request: Request) -> dict[str, Any]:
    """Update organization settings. Owner/manager only."""
    user = _require_user(request)
    with session_scope() as db:
        try:
            updates = body.model_dump(exclude_unset=True)
            return oq.update_org_settings(db, org_id, user.id, **updates)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@router.get("/{org_id}/audit")
def get_audit_log(
    org_id: int,
    request: Request,
    limit -> None:
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]] -> None:
    """Get audit log entries. Owner/manager only."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "audit_view"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view the audit log",
            )
        return oq.get_audit_log(db, org_id, limit=limit, offset=offset)
