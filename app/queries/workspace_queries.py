"""Workspace queries — shortlists and entry management.

Implementation split across:
- workspace_helpers.py: validation, status transitions, helper functions
- workspace_shortlists.py: shortlist CRUD operations
- workspace_entries.py: entry add/update/notes/tags/detail operations
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class ShortlistNotFound(ValueError):
    """Shortlist not found or not owned — HTTP 404."""


class PlayerNotFound(ValueError):
    """Player not found — HTTP 404."""


class InvalidStatusTransition(ValueError):
    """Invalid status transition — HTTP 400."""


class DuplicateEntry(ValueError):
    """Player already in shortlist — HTTP 409."""


class WorkspaceLimitExceeded(ValueError):
    """Free-tier shortlist cap reached — honest upsell message."""


def validate_transition(from_status: str | None, to_status: str) -> str | None:
    """Validate and return error message if transition is invalid."""
    TRANSITIONS = {
        None: {"Wishlist", "Watching", "Shortlisted", "Rejected"},
        "Wishlist": {"Watching", "Shortlisted", "Rejected"},
        "Watching": {"Shortlisted", "Rejected", "Wishlist"},
        "Shortlisted": {"Watching", "Rejected", "Wishlist"},
        "Rejected": {"Wishlist"},
    }
    valid = TRANSITIONS.get(from_status, set())
    if to_status not in valid:
        return f"Cannot move from '{from_status}' to '{to_status}'"
    return None


def _now() -> datetime:
    return datetime.now()


def _owned_shortlist(
    db: Session, user_id: int, shortlist_id: int
):
    from app.models import Shortlist
    sl = db.query(Shortlist).filter(
        Shortlist.id == shortlist_id, Shortlist.user_id == user_id
    ).first()
    if sl is None:
        raise ShortlistNotFound(f"shortlist {shortlist_id} not found")
    return sl


def _owned_entry(db: Session, user_id: int, entry_id: int):
    from app.models import ShortlistEntry
    entry = db.query(ShortlistEntry).filter(
        ShortlistEntry.id == entry_id,
        ShortlistEntry.shortlist_id.in_(
            db.query(ShortlistEntry.shortlist_id).filter(
                ShortlistEntry.id == entry_id
            ).subquery()
        ),
    ).first()
    if entry is None:
        raise ShortlistNotFound(f"entry {entry_id} not found")
    return entry


def _entry_counts(db: Session, shortlist_ids: list[int]) -> dict[int, dict[str, Any]]:
    from sqlalchemy import func
    from app.models import ShortlistEntry
    rows = (
        db.query(
            ShortlistEntry.shortlist_id,
            ShortlistEntry.status,
            func.count(ShortlistEntry.id),
        )
        .filter(ShortlistEntry.shortlist_id.in_(shortlist_ids))
        .group_by(ShortlistEntry.shortlist_id, ShortlistEntry.status)
        .all()
    )
    counts: dict[int, dict[str, Any]] = {sid: {"total": 0} for sid in shortlist_ids}
    for sid, status, cnt in rows:
        counts[sid][status] = cnt
        counts[sid]["total"] += cnt
    return counts


def _bump_shortlist(db: Session, shortlist_id: int) -> None:
    from app.models import Shortlist
    sl = db.query(Shortlist).filter(Shortlist.id == shortlist_id).first()
    if sl:
        sl.updated_at = _now()
        db.commit()


# Re-export from split modules
from app.queries.workspace_shortlists import (  # noqa: F401, E402
    ensure_default_shortlist,
    list_shortlists,
    create_shortlist,
    delete_shortlist,
)
from app.queries.workspace_entries import (  # noqa: F401, E402
    add_player_to_shortlist,
    update_entry_status,
    set_entry_priority,
    add_entry_note,
    add_entry_tag,
    remove_entry_tag,
    remove_entry,
    remove_entry_by_id,
    get_shortlist_memberships,
    get_shortlist_detail,
    get_user_tag_suggestions,
)
