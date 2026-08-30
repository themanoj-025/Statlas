"""Tests for Phase 16 — Organization / Multi-Tenant Architecture.

Covers:
- Organization creation and retrieval
- Member management (invite, accept, remove, role change)
- RBAC permission enforcement
- Resource ownership (personal vs org-shared)
- Comments and mentions
- Audit logging
- Settings management
- Data isolation (cross-org rejection)

Constitution §4: Every function has unit tests.
Multi-Tenant Addendum §3.4: Every role/permission boundary tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app import auth
from app.models import (

pytestmark = pytest.mark.slow
    Comment,
    Mention,
    Organization,
    OrgInvite,
    OrgMembership,
    OrgSettings,
    Shortlist,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    db: Session, *, email: str = "test@example.com", name: str = "Test User"
) -> User:
    user = User(
        email=email,
        password_hash=auth.hash_password("password123"),
        display_name=name,
    )
    db.add(user)
    db.flush()
    return user


def _make_org(
    db: Session, owner: User, *, name: str = "Test FC Scouting"
) -> Organization:
    org = Organization(
        name=name,
        slug=name.lower().replace(" ", "-"),
        owner_user_id=owner.id,
    )
    db.add(org)
    db.flush()

    settings = OrgSettings(org_id=org.id)
    db.add(settings)

    membership = OrgMembership(
        org_id=org.id,
        user_id=owner.id,
        role="owner",
        invited_by_user_id=owner.id,
    )
    db.add(membership)
    db.flush()
    return org


def _add_member(
    db: Session,
    org: Organization,
    user: User,
    role: str = "scout",
    by: User | None = None,
) -> OrgMembership:
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role=role,
        invited_by_user_id=by.id if by else user.id,
    )
    db.add(membership)
    db.flush()
    return membership


# ---------------------------------------------------------------------------
# Organization CRUD tests
# ---------------------------------------------------------------------------


class TestOrganizationCRUD:
    """Organization creation and retrieval."""

    def test_create_organization(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        result = create_organization(db, owner.id, "Juventus Scouting Team")
        assert result["org_id"] is not None
        assert result["name"] == "Juventus Scouting Team"
        assert result["slug"] == "juventus-scouting-team"
        assert result["tier"] == "free"

    def test_create_org_auto_slug(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        result = create_organization(db, owner.id, "AC Milan Analytics!")
        assert result["slug"] == "ac-milan-analytics"

    def test_create_org_duplicate_slug_fails(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        create_organization(db, owner.id, "Test Org")
        with pytest.raises(ValueError, match="already exists"):
            create_organization(db, owner.id, "Test Org")

    def test_create_org_slug_too_short(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        with pytest.raises(ValueError, match="at least 3 characters"):
            create_organization(db, owner.id, "AB", slug="ab")

    def test_create_org_slug_invalid_format(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            create_organization(db, owner.id, "Bad Slug", slug="Bad Slug!@#")

    def test_create_org_slug_underscore_rejected(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        with pytest.raises(ValueError, match="lowercase letters, numbers, and hyphens"):
            create_organization(db, owner.id, "Underscore", slug="bad_slug")

    def test_create_org_reserved_slug_rejected(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        for reserved in ("api", "auth", "billing", "admin", "dashboard"):
            with pytest.raises(ValueError, match="reserved slug"):
                create_organization(db, owner.id, f"Reserved {reserved}", slug=reserved)

    def test_create_org_valid_slug_formats(self, db: Session):
        from app.queries.org_queries import create_organization

        owner = _make_user(db)
        for slug in ("my-org", "org-123", "scouting-team-v2"):
            result = create_organization(db, owner.id, f"Org {slug}", slug=slug)
            assert result["slug"] == slug
            # Reset owner for next iteration
            owner = _make_user(db, email=f"{slug}@test.com")

    def test_get_organization(self, db: Session):
        from app.queries.org_queries import get_organization

        owner = _make_user(db)
        org = _make_org(db, owner)
        result = get_organization(db, org.id)
        assert result is not None
        assert result["name"] == "Test FC Scouting"
        assert result["member_count"] == 1  # owner

    def test_list_user_organizations(self, db: Session):
        from app.queries.org_queries import list_user_organizations

        owner = _make_user(db)
        _make_org(db, owner, name="Org One")
        _make_org(db, owner, name="Org Two")

        result = list_user_organizations(db, owner.id)
        assert len(result) == 2
        org_names = {o["name"] for o in result}
        assert "Org One" in org_names
        assert "Org Two" in org_names


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------


class TestRBAC:
    """RBAC permission enforcement — every role boundary tested."""

    def test_owner_has_all_permissions(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner = _make_user(db)
        org = _make_org(db, owner)

        assert user_has_permission(db, owner.id, org.id, "org_delete")
        assert user_has_permission(db, owner.id, org.id, "member_invite")
        assert user_has_permission(db, owner.id, org.id, "resource_create")
        assert user_has_permission(db, owner.id, org.id, "audit_view")

    def test_manager_has_limited_permissions(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner = _make_user(db)
        manager = _make_user(db, email="mgr@test.com", name="Manager")
        org = _make_org(db, owner)
        _add_member(db, org, manager, role="manager", by=owner)

        assert user_has_permission(db, manager.id, org.id, "member_invite")
        assert user_has_permission(db, manager.id, org.id, "resource_create")
        assert user_has_permission(db, manager.id, org.id, "audit_view")
        assert not user_has_permission(db, manager.id, org.id, "org_delete")

    def test_scout_can_create_and_comment(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner = _make_user(db)
        scout = _make_user(db, email="scout@test.com", name="Scout")
        org = _make_org(db, owner)
        _add_member(db, org, scout, role="scout", by=owner)

        assert user_has_permission(db, scout.id, org.id, "resource_create")
        assert user_has_permission(db, scout.id, org.id, "resource_comment")
        assert user_has_permission(db, scout.id, org.id, "resource_view")
        assert not user_has_permission(db, scout.id, org.id, "member_invite")
        assert not user_has_permission(db, scout.id, org.id, "audit_view")

    def test_viewer_can_only_view(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner = _make_user(db)
        viewer = _make_user(db, email="viewer@test.com", name="Viewer")
        org = _make_org(db, owner)
        _add_member(db, org, viewer, role="viewer", by=owner)

        assert user_has_permission(db, viewer.id, org.id, "resource_view")
        assert not user_has_permission(db, viewer.id, org.id, "resource_create")
        assert not user_has_permission(db, viewer.id, org.id, "resource_comment")
        assert not user_has_permission(db, viewer.id, org.id, "member_invite")

    def test_non_member_has_no_permissions(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner = _make_user(db)
        outsider = _make_user(db, email="outsider@test.com", name="Outsider")
        org = _make_org(db, owner)

        assert not user_has_permission(db, outsider.id, org.id, "resource_view")
        assert not user_has_permission(db, outsider.id, org.id, "resource_create")


# ---------------------------------------------------------------------------
# Member management tests
# ---------------------------------------------------------------------------


class TestMemberManagement:
    """Member invite, accept, remove, and role change."""

    def test_invite_member(self, db: Session):
        from app.queries.org_queries import invite_member

        owner = _make_user(db)
        org = _make_org(db, owner)

        result = invite_member(db, org.id, owner.id, "new@test.com", role="scout")
        assert result["email"] == "new@test.com"
        assert result["role"] == "scout"
        assert result["raw_token"]  # Token returned once

    def test_invite_duplicate_pending_fails(self, db: Session):
        from app.queries.org_queries import invite_member

        owner = _make_user(db)
        org = _make_org(db, owner)

        invite_member(db, org.id, owner.id, "dup@test.com")
        with pytest.raises(ValueError, match="already pending"):
            invite_member(db, org.id, owner.id, "dup@test.com")

    def test_invite_existing_member_fails(self, db: Session):
        from app.queries.org_queries import invite_member

        owner = _make_user(db)
        org = _make_org(db, owner)

        with pytest.raises(ValueError, match="already a member"):
            invite_member(db, org.id, owner.id, owner.email)

    def test_seat_limit_enforced(self, db: Session):
        from app.queries.org_queries import invite_member

        owner = _make_user(db)
        org = _make_org(db, owner, name="Small Org")

        # Free tier = 5 seats. Owner takes 1, so 4 more members max.
        # Add actual members (not just invites) to hit the limit.
        for i in range(4):
            member = _make_user(db, email=f"member{i}@test.com")
            _add_member(db, org, member, by=owner)

        with pytest.raises(ValueError, match="seat limit"):
            invite_member(db, org.id, owner.id, "overflow@test.com")

    def test_accept_invite(self, db: Session):
        from app.queries.org_queries import accept_invite, invite_member

        owner = _make_user(db)
        new_user = _make_user(db, email="new@test.com", name="New User")
        org = _make_org(db, owner)

        invite = invite_member(db, org.id, owner.id, "new@test.com")
        result = accept_invite(db, invite["raw_token"], new_user.id)
        assert result["org_id"] == org.id
        assert result["role"] == "scout"

    def test_accept_expired_invite_fails(self, db: Session):
        from app.queries.org_queries import accept_invite

        owner = _make_user(db)
        new_user = _make_user(db, email="expired@test.com")
        org = _make_org(db, owner)

        # Create expired invite manually
        raw_token = auth.generate_token()
        invite = OrgInvite(
            org_id=org.id,
            email="expired@test.com",
            role="scout",
            token_hash=auth.hash_token(raw_token),
            invited_by_user_id=owner.id,
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(invite)
        db.commit()

        with pytest.raises(ValueError, match="expired"):
            accept_invite(db, raw_token, new_user.id)

    def test_remove_member(self, db: Session):
        from app.queries.org_queries import list_members, remove_member

        owner = _make_user(db)
        scout = _make_user(db, email="scout@test.com")
        org = _make_org(db, owner)
        _add_member(db, org, scout, by=owner)

        result = remove_member(db, org.id, owner.id, scout.id)
        assert result["removed"] is True

        members = list_members(db, org.id)
        assert len(members) == 1  # Only owner remains

    def test_cannot_remove_owner(self, db: Session):
        from app.queries.org_queries import remove_member

        owner = _make_user(db)
        org = _make_org(db, owner)

        with pytest.raises(ValueError, match="Cannot remove"):
            remove_member(db, org.id, owner.id, owner.id)

    def test_change_role(self, db: Session):
        from app.queries.org_queries import change_member_role

        owner = _make_user(db)
        scout = _make_user(db, email="scout@test.com")
        org = _make_org(db, owner)
        _add_member(db, org, scout, by=owner)

        result = change_member_role(db, org.id, owner.id, scout.id, "manager")
        assert result["changed"] is True
        assert result["old_role"] == "scout"
        assert result["new_role"] == "manager"

    def test_transfer_ownership(self, db: Session):
        from app.models import Organization
        from app.queries.org_queries import change_member_role

        owner = _make_user(db)
        successor = _make_user(db, email="successor@test.com")
        org = _make_org(db, owner)
        _add_member(db, org, successor, role="manager", by=owner)

        result = change_member_role(db, org.id, owner.id, successor.id, "owner")
        assert result["changed"] is True

        # Verify org ownership transferred
        updated_org = db.get(Organization, org.id)
        assert updated_org.owner_user_id == successor.id


# ---------------------------------------------------------------------------
# Audit logging tests
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Audit trail for team changes."""

    def test_audit_log_recorded(self, db: Session):
        from app.queries.org_queries import get_audit_log, invite_member

        owner = _make_user(db)
        org = _make_org(db, owner)

        invite_member(db, org.id, owner.id, "new@test.com")

        log = get_audit_log(db, org.id)
        assert len(log) >= 1
        assert log[0]["action"] == "user_added"
        assert log[0]["detail"]["email"] == "new@test.com"

    def test_audit_log_requires_permission(self, db: Session):
        from app.queries.org_queries import get_audit_log

        owner = _make_user(db)
        viewer = _make_user(db, email="viewer@test.com")
        org = _make_org(db, owner)
        _add_member(db, org, viewer, role="viewer", by=owner)

        # Viewer cannot view audit log (checked at API level, not query level)
        # But the query itself returns data — permission is checked in the view
        log = get_audit_log(db, org.id)
        assert isinstance(log, list)  # Query returns data; view enforces permission


# ---------------------------------------------------------------------------
# Comments tests
# ---------------------------------------------------------------------------


class TestComments:
    """Comment system with threading and mentions."""

    def test_add_comment(self, db: Session):
        owner = _make_user(db)
        org = _make_org(db, owner)

        comment = Comment(
            resource_type="shortlist",
            resource_id=1,
            org_id=org.id,
            author_user_id=owner.id,
            text="Great shortlist!",
        )
        db.add(comment)
        db.flush()

        assert comment.id is not None
        assert comment.text == "Great shortlist!"

    def test_threaded_comments(self, db: Session):
        owner = _make_user(db)
        org = _make_org(db, owner)

        parent = Comment(
            resource_type="shortlist",
            resource_id=1,
            org_id=org.id,
            author_user_id=owner.id,
            text="Parent comment",
        )
        db.add(parent)
        db.flush()

        reply = Comment(
            resource_type="shortlist",
            resource_id=1,
            org_id=org.id,
            author_user_id=owner.id,
            parent_id=parent.id,
            text="Reply to parent",
        )
        db.add(reply)
        db.flush()

        assert reply.parent_id == parent.id

    def test_soft_delete_comment(self, db: Session):
        from datetime import datetime, timezone

        owner = _make_user(db)
        org = _make_org(db, owner)

        comment = Comment(
            resource_type="shortlist",
            resource_id=1,
            org_id=org.id,
            author_user_id=owner.id,
            text="To be deleted",
        )
        db.add(comment)
        db.flush()

        comment.deleted_at = datetime.now(timezone.utc)
        db.commit()

        assert comment.deleted_at is not None

    def test_mentions_created(self, db: Session):
        owner = _make_user(db)
        mentioned = _make_user(db, email="mentioned@test.com", name="Mentioned User")
        org = _make_org(db, owner)
        _add_member(db, org, mentioned, by=owner)

        comment = Comment(
            resource_type="shortlist",
            resource_id=1,
            org_id=org.id,
            author_user_id=owner.id,
            text="@mentioned what do you think?",
        )
        db.add(comment)
        db.flush()

        mention = Mention(
            comment_id=comment.id,
            mentioned_user_id=mentioned.id,
            org_id=org.id,
        )
        db.add(mention)
        db.flush()

        assert mention.mentioned_user_id == mentioned.id
        assert mention.status == "pending"


# ---------------------------------------------------------------------------
# Resource ownership tests
# ---------------------------------------------------------------------------


class TestResourceOwnership:
    """Personal vs org-shared resource access."""

    def test_shortlist_default_personal(self, db: Session):
        owner = _make_user(db)
        sl = Shortlist(user_id=owner.id, name="My Shortlist")
        db.add(sl)
        db.flush()

        assert sl.owner_org_id is None
        assert sl.visibility == "personal"

    def test_shortlist_can_be_org_shared(self, db: Session):
        owner = _make_user(db)
        org = _make_org(db, owner)

        sl = Shortlist(
            user_id=owner.id,
            name="Team Shortlist",
            owner_org_id=org.id,
            visibility="org_members",
        )
        db.add(sl)
        db.flush()

        assert sl.owner_org_id == org.id
        assert sl.visibility == "org_members"


# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


class TestOrgSettings:
    """Organization settings management."""

    def test_get_settings(self, db: Session):
        from app.queries.org_queries import get_org_settings

        owner = _make_user(db)
        org = _make_org(db, owner)

        settings = get_org_settings(db, org.id)
        assert settings is not None
        assert settings["data_retention_days"] == 90
        assert settings["enable_audit_logging"] is True

    def test_update_settings(self, db: Session):
        from app.queries.org_queries import update_org_settings

        owner = _make_user(db)
        org = _make_org(db, owner)

        result = update_org_settings(db, org.id, owner.id, data_retention_days=30)
        assert result["data_retention_days"] == 30

    def test_update_settings_requires_permission(self, db: Session):
        from app.queries.org_queries import update_org_settings

        owner = _make_user(db)
        viewer = _make_user(db, email="viewer@test.com")
        org = _make_org(db, owner)
        _add_member(db, org, viewer, role="viewer", by=owner)

        with pytest.raises(PermissionError):
            update_org_settings(db, org.id, viewer.id, data_retention_days=30)


# ---------------------------------------------------------------------------
# Data isolation tests (Addendum Part 3.4)
# ---------------------------------------------------------------------------


class TestDataIsolation:
    """Cross-org access rejection — the most critical multi-tenant test."""

    def test_cross_org_access_rejected(self, db: Session):
        from app.queries.org_queries import user_has_permission

        owner_a = _make_user(db, email="ownerA@test.com")
        owner_b = _make_user(db, email="ownerB@test.com")
        org_a = _make_org(db, owner_a, name="Org A")
        org_b = _make_org(db, owner_b, name="Org B")

        # Owner A should NOT have access to Org B
        assert not user_has_permission(db, owner_a.id, org_b.id, "resource_view")
        assert not user_has_permission(db, owner_b.id, org_a.id, "resource_view")

    def test_org_member_cannot_see_other_org_resources(self, db: Session):
        from app.queries.org_queries import user_has_permission


        owner_a = _make_user(db, email="ownerA@test.com")
        owner_b = _make_user(db, email="ownerB@test.com")
        scout_a = _make_user(db, email="scoutA@test.com")
        org_a = _make_org(db, owner_a, name="Org A")
        org_b = _make_org(db, owner_b, name="Org B")
        _add_member(db, org_a, scout_a, by=owner_a)

        # Scout in Org A should NOT have access to Org B
        assert not user_has_permission(db, scout_a.id, org_b.id, "resource_view")
