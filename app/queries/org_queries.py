"""Organization queries — RBAC enforcement, membership management, and resource access.

Constitution §4: Every read/write checks membership + role before returning data.
Multi-Tenant Addendum §3.1: RBAC permission matrix enforced consistently.

RBAC Roles and Permissions (Addendum Part 3.1):
- owner:  full access, can delete org, manage billing, all member actions
- manager: invite/remove members, change roles, manage shared resources, view audit
- scout: create/edit own resources, comment, view org resources
- viewer: read-only access to org resources, no create/comment
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app import auth
from app.models import (
    AuditLog,
    Organization,
    OrgInvite,
    OrgMembership,
    OrgSettings,
    Shortlist,
    User,
)

# ---------------------------------------------------------------------------
# RBAC Permission Matrix (Addendum Part 3.1)
# ---------------------------------------------------------------------------

# Permissions per role (inclusive: higher roles inherit lower role permissions)
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "org_delete",
        "org_settings_edit",
        "billing_manage",
        "member_invite",
        "member_remove",
        "member_role_change",
        "resource_create",
        "resource_edit",
        "resource_delete",
        "resource_share",
        "resource_comment",
        "resource_view",
        "audit_view",
    },
    "manager": {
        "member_invite",
        "member_remove",
        "member_role_change",
        "resource_create",
        "resource_edit",
        "resource_delete",
        "resource_share",
        "resource_comment",
        "resource_view",
        "audit_view",
    },
    "scout": {
        "resource_create",
        "resource_edit",
        "resource_delete",
        "resource_comment",
        "resource_view",
    },
    "viewer": {
        "resource_view",
    },
}


def user_has_permission(
    db: Session,
    user_id: int,
    org_id: int,
    permission: str,
) -> bool:
    """Check if a user has a specific permission within an organization.

    This is THE single permission-check function used across the backend.
    Every query that filters by org context must call this first.

    Returns False for non-members (silent denial — no existence leak).
    """
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    if membership is None:
        return False

    # Check permissions_override for granular exceptions
    if membership.permissions_override:
        override = membership.permissions_override
        if permission in override:
            return override[permission]  # True or False override

    # Check role-based permissions
    role_perms = ROLE_PERMISSIONS.get(membership.role, set())
    return permission in role_perms


def get_user_org_ids(db: Session, user_id: int) -> list[int]:
    """Return all org IDs the user is a member of."""
    memberships = (
        db.query(OrgMembership.org_id).filter(OrgMembership.user_id == user_id).all()
    )
    return [m.org_id for m in memberships]


def get_user_org_role(db: Session, user_id: int, org_id: int) -> str | None:
    """Return the user's role in an org, or None if not a member."""
    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    return membership.role if membership else None


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


def create_organization(
    db: Session,
    owner_user_id: int,
    name: str,
    *,
    slug: str | None = None,
    country: str | None = None,
    primary_contact_email: str | None = None,
) -> dict[str, Any]:
    """Create a new organization. The creator becomes the owner.

    Non-destructive: existing solo data stays personal.
    """
    import re

    if slug is None:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:128]

    # Check slug uniqueness
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise ValueError(f"Organization slug '{slug}' already exists")

    owner = db.get(User, owner_user_id)
    if owner is None:
        raise ValueError("User not found")

    org = Organization(
        name=name,
        slug=slug,
        owner_user_id=owner_user_id,
        primary_contact_email=primary_contact_email or owner.email,
        country=country,
    )
    db.add(org)
    db.flush()

    # Create default settings
    settings = OrgSettings(org_id=org.id)
    db.add(settings)

    # Add owner as member with owner role
    membership = OrgMembership(
        org_id=org.id,
        user_id=owner_user_id,
        role="owner",
        invited_by_user_id=owner_user_id,
    )
    db.add(membership)

    # Audit log
    _log_audit(db, org.id, owner_user_id, "resource_created", detail={"name": name})

    db.commit()
    return {
        "org_id": org.id,
        "name": org.name,
        "slug": org.slug,
        "tier": org.tier,
        "owner_user_id": org.owner_user_id,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


def get_organization(db: Session, org_id: int) -> dict[str, Any] | None:
    """Get organization details."""
    org = db.get(Organization, org_id)
    if org is None:
        return None
    member_count = (
        db.query(OrgMembership).filter(OrgMembership.org_id == org_id).count()
    )
    return {
        "org_id": org.id,
        "name": org.name,
        "slug": org.slug,
        "tier": org.tier,
        "owner_user_id": org.owner_user_id,
        "member_count": member_count,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "country": org.country,
    }


def list_user_organizations(db: Session, user_id: int) -> list[dict[str, Any]]:
    """List all organizations a user belongs to."""
    memberships = (
        db.query(OrgMembership, Organization)
        .join(Organization, OrgMembership.org_id == Organization.id)
        .filter(OrgMembership.user_id == user_id)
        .all()
    )
    return [
        {
            "org_id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": m.role,
            "tier": org.tier,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m, org in memberships
    ]


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


def invite_member(
    db: Session,
    org_id: int,
    invited_by_user_id: int,
    email: str,
    role: str = "scout",
) -> dict[str, Any]:
    """Invite a user to an organization by email.

    Generates a time-limited invite token. The invite can be accepted by
    an existing user or a new user (who must sign up first).
    """
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {role}")

    # Check inviter has permission
    if not user_has_permission(db, invited_by_user_id, org_id, "member_invite"):
        raise PermissionError("You do not have permission to invite members")

    # Check seat limit
    org = db.get(Organization, org_id)
    if org is None:
        raise ValueError("Organization not found")

    member_count = (
        db.query(OrgMembership).filter(OrgMembership.org_id == org_id).count()
    )

    seat_limits = {"free": 5, "pro": 25, "enterprise": 100}
    max_seats = seat_limits.get(org.tier, 5)
    if member_count >= max_seats:
        raise ValueError(
            f"Organization has reached its {max_seats}-seat limit. Upgrade to add more members."
        )

    # Check for existing pending invite
    existing_invite = (
        db.query(OrgInvite)
        .filter(
            OrgInvite.org_id == org_id,
            OrgInvite.email == email,
            OrgInvite.status == "pending",
        )
        .first()
    )
    if existing_invite:
        raise ValueError(f"An invite is already pending for {email}")

    # Check if already a member
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        existing_member = (
            db.query(OrgMembership)
            .filter(
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == existing_user.id,
            )
            .first()
        )
        if existing_member:
            raise ValueError(f"{email} is already a member of this organization")

    # Create invite token
    raw_token = auth.generate_token()
    token_hash = auth.hash_token(raw_token)

    invite = OrgInvite(
        org_id=org_id,
        email=email,
        role=role,
        token_hash=token_hash,
        invited_by_user_id=invited_by_user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)

    # Audit log
    _log_audit(
        db,
        org_id,
        invited_by_user_id,
        "user_added",
        detail={"email": email, "role": role},
    )

    db.commit()
    return {
        "invite_id": invite.id,
        "email": email,
        "role": role,
        "expires_at": invite.expires_at.isoformat(),
        "raw_token": raw_token,  # Only returned once — for email delivery
    }


def accept_invite(db: Session, raw_token: str, user_id: int) -> dict[str, Any]:
    """Accept an org invitation. Adds the user as a member."""
    token_hash = auth.hash_token(raw_token)

    invite = db.query(OrgInvite).filter(OrgInvite.token_hash == token_hash).first()
    if invite is None:
        raise ValueError("Invalid invite token")

    if invite.status != "pending":
        raise ValueError("This invite has already been used")

    now = datetime.now(timezone.utc)
    if invite.expires_at.tzinfo is None:
        invite.expires_at = invite.expires_at.replace(tzinfo=timezone.utc)
    if invite.expires_at < now:
        invite.status = "expired"
        db.commit()
        raise ValueError("This invite has expired")

    # Check user is not already a member
    existing = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == invite.org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    if existing:
        raise ValueError("You are already a member of this organization")

    # Add membership
    membership = OrgMembership(
        org_id=invite.org_id,
        user_id=user_id,
        role=invite.role,
        invited_by_user_id=invite.invited_by_user_id,
    )
    db.add(membership)

    # Mark invite as accepted
    invite.status = "accepted"
    invite.accepted_at = now

    # Audit log
    _log_audit(
        db,
        invite.org_id,
        invite.invited_by_user_id,
        "user_added",
        target_user_id=user_id,
        detail={"role": invite.role},
    )

    db.commit()
    return {
        "org_id": invite.org_id,
        "role": invite.role,
        "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
    }


def remove_member(
    db: Session,
    org_id: int,
    removed_by_user_id: int,
    target_user_id: int,
) -> dict[str, Any]:
    """Remove a member from an organization.

    Data cleanup rules (Addendum §4.3):
    - Personal data (within their account) is untouched
    - Resources they created with visibility='personal' become inaccessible to org
    - Resources they created with visibility='org_members' remain (archived)
    """
    if not user_has_permission(db, removed_by_user_id, org_id, "member_remove"):
        raise PermissionError("You do not have permission to remove members")

    # Cannot remove the owner
    org = db.get(Organization, org_id)
    if org and org.owner_user_id == target_user_id:
        raise ValueError("Cannot remove the organization owner")

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == target_user_id,
        )
        .first()
    )
    if membership is None:
        raise ValueError("User is not a member of this organization")

    removed_role = membership.role
    db.delete(membership)

    # Audit log
    _log_audit(
        db,
        org_id,
        removed_by_user_id,
        "user_removed",
        target_user_id=target_user_id,
        detail={"previous_role": removed_role},
    )

    db.commit()
    return {"removed": True, "previous_role": removed_role}


def change_member_role(
    db: Session,
    org_id: int,
    changed_by_user_id: int,
    target_user_id: int,
    new_role: str,
) -> dict[str, Any]:
    """Change a member's role within an organization."""
    if new_role not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: {new_role}")

    if not user_has_permission(db, changed_by_user_id, org_id, "member_role_change"):
        raise PermissionError("You do not have permission to change member roles")

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == target_user_id,
        )
        .first()
    )
    if membership is None:
        raise ValueError("User is not a member of this organization")

    old_role = membership.role
    if old_role == new_role:
        return {"changed": False, "role": new_role}

    membership.role = new_role

    # If transferring ownership, update org
    if new_role == "owner":
        org = db.get(Organization, org_id)
        if org:
            # Demote current owner to manager
            old_owner_membership = (
                db.query(OrgMembership)
                .filter(
                    OrgMembership.org_id == org_id,
                    OrgMembership.user_id == org.owner_user_id,
                )
                .first()
            )
            if old_owner_membership and old_owner_membership.user_id != target_user_id:
                old_owner_membership.role = "manager"
            org.owner_user_id = target_user_id

    # Audit log
    _log_audit(
        db,
        org_id,
        changed_by_user_id,
        "role_changed",
        target_user_id=target_user_id,
        detail={"old_role": old_role, "new_role": new_role},
    )

    db.commit()
    return {"changed": True, "old_role": old_role, "new_role": new_role}


def list_members(db: Session, org_id: int) -> list[dict[str, Any]]:
    """List all members of an organization with their roles."""
    memberships = (
        db.query(OrgMembership, User)
        .join(User, OrgMembership.user_id == User.id)
        .filter(OrgMembership.org_id == org_id)
        .order_by(OrgMembership.joined_at)
        .all()
    )
    return [
        {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m, user in memberships
    ]


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _log_audit(
    db: Session,
    org_id: int,
    performed_by_user_id: int,
    action: str,
    *,
    target_user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Append an audit log entry. Never raises — audit failures are logged."""
    try:
        log_entry = AuditLog(
            org_id=org_id,
            action=action,
            performed_by_user_id=performed_by_user_id,
            target_user_id=target_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
        )
        db.add(log_entry)
    except Exception:
        pass  # Audit logging must never break the operation


def get_audit_log(
    db: Session,
    org_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get audit log entries for an organization. Owner/manager only."""
    entries = (
        db.query(AuditLog, User)
        .join(User, AuditLog.performed_by_user_id == User.id)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        {
            "id": log.id,
            "action": log.action,
            "performed_by": user.display_name or user.email,
            "performed_by_user_id": log.performed_by_user_id,
            "target_user_id": log.target_user_id,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, user in entries
    ]


# ---------------------------------------------------------------------------
# Org settings
# ---------------------------------------------------------------------------


def get_org_settings(db: Session, org_id: int) -> dict[str, Any] | None:
    """Get organization settings."""
    settings = db.query(OrgSettings).filter(OrgSettings.org_id == org_id).first()
    if settings is None:
        return None
    return {
        "org_id": settings.org_id,
        "data_retention_days": settings.data_retention_days,
        "workspace_name": settings.workspace_name,
        "enable_audit_logging": settings.enable_audit_logging,
        "allow_public_reporting": settings.allow_public_reporting,
        "require_2fa": settings.require_2fa,
    }


def update_org_settings(
    db: Session,
    org_id: int,
    user_id: int,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update organization settings. Owner/manager only."""
    if not user_has_permission(db, user_id, org_id, "org_settings_edit"):
        raise PermissionError("You do not have permission to edit org settings")

    settings = db.query(OrgSettings).filter(OrgSettings.org_id == org_id).first()
    if settings is None:
        # Create if missing
        settings = OrgSettings(org_id=org_id)
        db.add(settings)
        db.flush()

    for key, value in kwargs.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)

    db.commit()
    return get_org_settings(db, org_id)


# ---------------------------------------------------------------------------
# Resource access helpers (Part C2)
# ---------------------------------------------------------------------------


def get_user_shortlists(
    db: Session,
    user_id: int,
    *,
    org_id: int | None = None,
) -> list[dict[str, Any]]:
    """Get shortlists accessible to the user, including personal + org-shared.

    If org_id is provided, returns shortlists in that org context.
    If org_id is None, returns all accessible shortlists across all contexts.
    """
    from app.models import ShortlistEntry

    # Personal shortlists (always visible to the owner)
    personal = (
        db.query(Shortlist)
        .filter(
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            Shortlist.owner_org_id.is_(None),
        )
        .all()
    )

    results = []
    for sl in personal:
        entry_count = (
            db.query(ShortlistEntry)
            .filter(
                ShortlistEntry.shortlist_id == sl.id,
                ShortlistEntry.removed_at.is_(None),
            )
            .count()
        )
        results.append(
            {
                "shortlist_id": sl.id,
                "name": sl.name,
                "description": sl.description,
                "entry_count": entry_count,
                "visibility": getattr(sl, "visibility", "personal"),
                "owner_type": "personal",
                "created_at": sl.created_at.isoformat() if sl.created_at else None,
            }
        )

    # Org-shared shortlists
    user_org_ids = get_user_org_ids(db, user_id)
    if org_id is not None:
        user_org_ids = [oid for oid in user_org_ids if oid == org_id]

    if user_org_ids:
        org_shortlists = (
            db.query(Shortlist)
            .filter(
                Shortlist.owner_org_id.in_(user_org_ids),
                Shortlist.deleted_at.is_(None),
            )
            .all()
        )
        for sl in org_shortlists:
            # Check visibility access
            vis = getattr(sl, "visibility", "org_members")
            if vis == "personal" and sl.user_id != user_id:
                continue  # Other users' personal shortlists in org are hidden
            if vis == "restricted":
                restricted_access = getattr(sl, "restricted_access", None) or []
                if user_id not in restricted_access:
                    user_role = get_user_org_role(db, user_id, sl.owner_org_id)
                    if user_role not in ("owner", "manager"):
                        continue

            entry_count = (
                db.query(ShortlistEntry)
                .filter(
                    ShortlistEntry.shortlist_id == sl.id,
                    ShortlistEntry.removed_at.is_(None),
                )
                .count()
            )
            creator = db.get(User, sl.user_id)
            results.append(
                {
                    "shortlist_id": sl.id,
                    "name": sl.name,
                    "description": sl.description,
                    "entry_count": entry_count,
                    "visibility": vis,
                    "owner_type": "org",
                    "org_id": sl.owner_org_id,
                    "created_by": (
                        creator.display_name or creator.email if creator else None
                    ),
                    "created_at": sl.created_at.isoformat() if sl.created_at else None,
                }
            )

    return results
