"""Workspace — shortlist CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Player, Shortlist, ShortlistEntry
from app.queries.workspace_queries import (
    InvalidStatusTransition,
    ShortlistNotFound,
    WorkspaceLimitExceeded,
    _entry_counts,
    _now,
    _owned_shortlist,
    validate_transition,
)

# Shortlists
# ---------------------------------------------------------------------------


def ensure_default_shortlist(db: Session, user_id: int) -> Shortlist:
    """Lazily create the user's first shortlist ("My Shortlist") so the feature
    is never an empty, confusing void on first use (Phase 7 A1)."""
    existing = (
        db.query(Shortlist)
        .filter(Shortlist.user_id == user_id, Shortlist.deleted_at.is_(None))
        .first()
    )
    if existing is not None:
        return existing
    shortlist = Shortlist(
        user_id=user_id,
        name=DEFAULT_SHORTLIST_NAME,
        description=DEFAULT_SHORTLIST_DESCRIPTION,
    )
    db.add(shortlist)
    db.commit()
    return shortlist


def list_shortlists(db: Session, user_id: int) -> list[dict[str, Any]]:
    """All the user's shortlists with entry counts + status breakdowns.

    Called on the workspace overview; lazily creates the default shortlist
    when the user has none.
    """
    ensure_default_shortlist(db, user_id)
    rows = (
        db.query(Shortlist)
        .filter(Shortlist.user_id == user_id, Shortlist.deleted_at.is_(None))
        .order_by(Shortlist.updated_at.desc(), Shortlist.id.desc())
        .all()
    )
    counts = _entry_counts(db, [s.id for s in rows])
    return [
        {
            "shortlist_id": s.id,
            "name": s.name,
            "description": s.description,
            "entry_count": counts[s.id]["entry_count"],
            "status_breakdown": counts[s.id]["status_breakdown"],
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in rows
    ]


def create_shortlist(
    db: Session, user_id: int, name: str, description: str | None = None
) -> dict[str, Any] -> None:
    """Create a shortlist, enforcing the plan's shortlist cap."""
    name = (name or "").strip()
    if not name:
        raise ValueError("A shortlist needs a name.")
    if len(name) > 128:
        raise ValueError("Shortlist names are limited to 128 characters.")
    if description is not None and len(description) > 2000:
        raise ValueError("Shortlist descriptions are limited to 2000 characters.")

    plan = effective_plan(db, user_id)
    limits = plan_limits(plan)
    max_shortlists = limits.get("shortlists_max")
    if max_shortlists is not None:
        current = (
            db.query(Shortlist)
            .filter(Shortlist.user_id == user_id, Shortlist.deleted_at.is_(None))
            .count()
        )
        if current >= max_shortlists:
            raise WorkspaceLimitExceeded(
                f"You've used your {plan} plan's allowance of {max_shortlists} "
                f"shortlist{'s' if max_shortlists != 1 else ''}. Upgrade to Pro "
                "for unlimited shortlists — your saved players, notes and tags "
                "all stay put."
            )

    shortlist = Shortlist(
        user_id=user_id,
        name=name,
        description=(description or "").strip() or None,
    )
    db.add(shortlist)
    db.commit()
    return {"shortlist_id": shortlist.id, "name": shortlist.name}


def delete_shortlist(db: Session, user_id: int, shortlist_id: int) -> None:
    """Soft-delete a shortlist and its entries (audit trail preserved)."""
    shortlist = _owned_shortlist(db, user_id, shortlist_id)
    now = _now()
    shortlist.deleted_at = now
    db.query(ShortlistEntry).filter(ShortlistEntry.shortlist_id == shortlist_id).update(
        {ShortlistEntry.removed_at: now}
    )
    db.commit()

