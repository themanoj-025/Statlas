"""Phase 16 — Comments & Collaboration API routes.

Comments on shared resources (shortlists, reports, searches) with threading,
@mentions, and activity feeds. Every comment requires org membership.

Routes:
- GET /api/v1/comments/{resource_type}/{resource_id} — list comments
- POST /api/v1/comments/{resource_type}/{resource_id} — add comment
- PUT /api/v1/comments/{comment_id} — edit comment
- DELETE /api/v1/comments/{comment_id} — soft-delete comment
- GET /api/v1/comments/{resource_type}/{resource_id}/activity — activity feed
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import require_user
from app.db import session_scope
from app.models import Comment, Mention, User
from app.queries import org_queries as oq

router = APIRouter(prefix="/api/v1/comments", tags=["comments"])


def _require_user(request: Request):
    return require_user(request)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class AddCommentBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    parent_id: int | None = Field(default=None)


class EditCommentBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


# ---------------------------------------------------------------------------
# Comment CRUD
# ---------------------------------------------------------------------------


@router.get("/{resource_type}/{resource_id}")
def list_comments(
    resource_type: str,
    resource_id: int,
    request: Request,
    org_id: int = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List comments on a resource. Must be an org member with resource access."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_view"):
            raise HTTPException(status_code=403, detail="Access denied")

        comments = (
            db.query(Comment, User)
            .join(User, Comment.author_user_id == User.id)
            .filter(
                Comment.resource_type == resource_type,
                Comment.resource_id == resource_id,
                Comment.org_id == org_id,
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at)
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            {
                "comment_id": c.id,
                "author": u.display_name or u.email,
                "author_user_id": c.author_user_id,
                "text": c.text,
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "edited_at": c.edited_at.isoformat() if c.edited_at else None,
            }
            for c, u in comments
        ]


@router.post("/{resource_type}/{resource_id}", status_code=201)
def add_comment(
    resource_type: str,
    resource_id: int,
    body: AddCommentBody,
    request: Request,
    org_id: int = Query(...),
):
    """Add a comment to a resource. Parses @mentions for notifications."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_comment"):
            raise HTTPException(
                status_code=403, detail="You do not have permission to comment"
            )

        comment = Comment(
            resource_type=resource_type,
            resource_id=resource_id,
            org_id=org_id,
            author_user_id=user.id,
            parent_id=body.parent_id,
            text=body.text,
        )
        db.add(comment)
        db.flush()

        # Parse @mentions
        mention_pattern = re.compile(r"@(\w+(?:\.\w+)*)")
        mentioned_names = mention_pattern.findall(body.text)

        if mentioned_names:
            # Find mentioned users in the org
            org_members = oq.list_members(db, org_id)
            member_by_name = {}
            for m in org_members:
                name = (m.get("display_name") or "").lower().replace(" ", "")
                email_prefix = m["email"].split("@")[0].lower()
                member_by_name[name] = m["user_id"]
                member_by_name[email_prefix] = m["user_id"]

            for name in mentioned_names:
                mentioned_user_id = member_by_name.get(name.lower())
                if mentioned_user_id and mentioned_user_id != user.id:
                    mention = Mention(
                        comment_id=comment.id,
                        mentioned_user_id=mentioned_user_id,
                        org_id=org_id,
                    )
                    db.add(mention)

        # Audit log
        oq._log_audit(
            db,
            org_id,
            user.id,
            "comment_added",
            resource_type=resource_type,
            resource_id=resource_id,
            detail={"comment_id": comment.id},
        )

        db.commit()
        return {
            "comment_id": comment.id,
            "created_at": (
                comment.created_at.isoformat() if comment.created_at else None
            ),
        }


@router.put("/{comment_id}")
def edit_comment(comment_id: int, body: EditCommentBody, request: Request):
    """Edit a comment. Only the author can edit."""
    user = _require_user(request)
    with session_scope() as db:
        comment = db.get(Comment, comment_id)
        if comment is None or comment.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.author_user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the author can edit this comment"
            )

        comment.text = body.text
        comment.edited_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
        db.commit()
        return {"ok": True}


@router.delete("/{comment_id}")
def delete_comment(comment_id: int, request: Request):
    """Soft-delete a comment. Author or org manager/owner can delete."""
    user = _require_user(request)
    with session_scope() as db:
        comment = db.get(Comment, comment_id)
        if comment is None or comment.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Comment not found")

        # Author or manager/owner can delete
        is_author = comment.author_user_id == user.id
        is_manager = oq.user_has_permission(
            db, user.id, comment.org_id, "member_remove"
        )
        if not is_author and not is_manager:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this comment",
            )

        from datetime import datetime, timezone

        comment.deleted_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True}


@router.get("/{resource_type}/{resource_id}/activity")
def activity_feed(
    resource_type: str,
    resource_id: int,
    request: Request,
    org_id: int = Query(...),
    limit: int = Query(50, ge=1, le=200),
):
    """Get activity feed for a resource (comments + status changes)."""
    user = _require_user(request)
    with session_scope() as db:
        if not oq.user_has_permission(db, user.id, org_id, "resource_view"):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get comments as activity items
        comments = (
            db.query(Comment, User)
            .join(User, Comment.author_user_id == User.id)
            .filter(
                Comment.resource_type == resource_type,
                Comment.resource_id == resource_id,
                Comment.org_id == org_id,
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at.desc())
            .limit(limit)
            .all()
        )

        activities = []
        for c, u in comments:
            activities.append(
                {
                    "type": "comment",
                    "user": u.display_name or u.email,
                    "user_id": c.author_user_id,
                    "text": c.text[:200],  # Truncate for feed
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )

        # Sort by created_at descending
        activities.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return activities[:limit]
