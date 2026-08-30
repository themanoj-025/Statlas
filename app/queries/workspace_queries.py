"""Phase 7 — Scouting workspace query layer.

The single service layer behind every workspace API route. Rules enforced
here (all documented in docs/product/scouting-pipeline.md):

- OWNERSHIP: every function takes the requesting user_id and verifies it on
  every read/write. A missing OR foreign shortlist/entry raises
  ShortlistNotFound (mapped to HTTP 404 by the API) — never a 403 that would
  leak existence.
- PIPELINE: status transitions are validated by `validate_transition`
  (forward skips + backward moves allowed within the chain; rejected exits
  only via monitoring; signed is terminal). Same-status is a no-op.
- SOFT DELETE: remove_entry / delete_shortlist set removed_at/deleted_at;
  notes, tags and status_history are never destroyed.
- TIER CAPS: Free = 1 shortlist, 10 entries per shortlist (pricing.json).
  Exceeding a cap raises WorkspaceLimitExceeded (403 + honest upsell copy).
- UNIQUE (shortlist_id, player_id): a player once per shortlist; adding an
  already-present player raises DuplicateEntry (409).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import effective_plan
from app.config import load_registry, plan_limits
from app.models import (
    EntryNote,
    EntryTag,
    League,
    PercentileSnapshot,
    Player,
    Shortlist,
    ShortlistEntry,
    StatSnapshot,
    StatusHistory,
    Team,
)
from app.queries.player_queries import _compact_slug_map

# ---------------------------------------------------------------------------
# Pipeline definition (docs/product/scouting-pipeline.md §1)
# ---------------------------------------------------------------------------

PIPELINE_ORDER = ["discovered", "monitoring", "scouted", "shortlisted", "reviewed"]
TERMINAL_STATUSES = {"rejected", "signed"}
ALL_STATUSES = [*PIPELINE_ORDER, "rejected", "signed"]
PRIORITIES = ("low", "medium", "high")

DEFAULT_SHORTLIST_NAME = "My Shortlist"
DEFAULT_SHORTLIST_DESCRIPTION = (
    "Your personal scouting workspace — add players you're tracking, tag them, "
    "and move them through the pipeline."
)


class ShortlistNotFound(ValueError):
    """Missing OR not owned — mapped to 404 (existence must not leak)."""


class PlayerNotFound(ValueError):
    """player_id does not exist."""


class InvalidStatusTransition(ValueError):
    """The requested status change violates the documented pipeline rules."""


class DuplicateEntry(ValueError):
    """The player is already in this shortlist."""


class WorkspaceLimitExceeded(ValueError):
    """Free-tier cap reached — the message is an honest, specific upsell."""


def validate_transition(from_status: str | None, to_status: str) -> str | None:
    """Return an error message for an invalid transition, else None.

    Rules (scouting-pipeline.md §1.1): forward skips and backward moves are
    allowed within the linear chain; any status may move to rejected/signed;
    rejected exits only via monitoring; signed is terminal; same-status is a
    no-op.
    """
    if to_status not in ALL_STATUSES:
        return f"Unknown status '{to_status}'."
    if from_status == to_status:
        return None  # no-op — no history row written
    if from_status == "signed":
        return (
            "Signed is a terminal status — a signed player can't be moved back "
            "through the pipeline. Remove the entry (history is preserved) if "
            "the situation changed."
        )
    if from_status == "rejected":
        if to_status == "monitoring":
            return None  # the one documented reconsideration path
        return (
            "A rejected player can only be reconsidered by moving them back to "
            "Monitoring first, then continuing the pipeline from there."
        )
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Ownership helpers
# ---------------------------------------------------------------------------


def _owned_shortlist(
    db: Session, user_id: int, shortlist_id: int, *, include_deleted: bool = False
) -> Shortlist:
    query = db.query(Shortlist).filter(
        Shortlist.id == shortlist_id, Shortlist.user_id == user_id
    )
    if not include_deleted:
        query = query.filter(Shortlist.deleted_at.is_(None))
    shortlist = query.first()
    if shortlist is None:
        raise ShortlistNotFound(f"shortlist {shortlist_id} not found")
    return shortlist


def _owned_entry(db: Session, user_id: int, entry_id: int) -> ShortlistEntry:
    entry = (
        db.query(ShortlistEntry)
        .join(Shortlist, ShortlistEntry.shortlist_id == Shortlist.id)
        .filter(
            ShortlistEntry.id == entry_id,
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            ShortlistEntry.removed_at.is_(None),
        )
        .first()
    )
    if entry is None:
        raise ShortlistNotFound(f"entry {entry_id} not found")
    return entry


def _entry_counts(db: Session, shortlist_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Total + per-status counts for the given shortlists (removed excluded)."""
    if not shortlist_ids:
        return {}
    rows = (
        db.query(
            ShortlistEntry.shortlist_id,
            ShortlistEntry.status,
            func.count(ShortlistEntry.id),
        )
        .filter(
            ShortlistEntry.shortlist_id.in_(shortlist_ids),
            ShortlistEntry.removed_at.is_(None),
        )
        .group_by(ShortlistEntry.shortlist_id, ShortlistEntry.status)
        .all()
    )
    out: dict[int, dict[str, Any]] = {
        sid: {"entry_count": 0, "status_breakdown": dict.fromkeys(ALL_STATUSES, 0)}
        for sid in shortlist_ids
    }
    for shortlist_id, status, count in rows:
        out[shortlist_id]["status_breakdown"][status] = count
        out[shortlist_id]["entry_count"] += count
    return out


def _bump_shortlist(db: Session, shortlist_id: int) -> None:
    shortlist = db.get(Shortlist, shortlist_id)
    if shortlist is not None:
        shortlist.updated_at = _now()


# ---------------------------------------------------------------------------
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
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


def add_player_to_shortlist(
    db: Session,
    user_id: int,
    shortlist_id: int,
    player_id: int,
    initial_note: str | None = None,
) -> dict[str, Any]:
    """Add a player to a shortlist: validates the player exists, defaults the
    status to `discovered`, records the add-time note and writes the initial
    status_history row."""
    _owned_shortlist(db, user_id, shortlist_id)

    player = db.get(Player, player_id)
    if player is None:
        raise PlayerNotFound(f"No player with id {player_id} exists.")

    # Free-tier entry cap (honest upsell, never a generic error).
    plan = effective_plan(db, user_id)
    limits = plan_limits(plan)
    max_entries = limits.get("shortlist_entries_max")
    if max_entries is not None:
        current = (
            db.query(ShortlistEntry)
            .filter(
                ShortlistEntry.shortlist_id == shortlist_id,
                ShortlistEntry.removed_at.is_(None),
            )
            .count()
        )
        if current >= max_entries:
            raise WorkspaceLimitExceeded(
                f"You've reached the {plan} plan's limit of {max_entries} players "
                "per shortlist. Upgrade to Pro for unlimited player tracking — "
                "your existing players, notes and tags stay put."
            )

    existing = (
        db.query(ShortlistEntry)
        .filter(
            ShortlistEntry.shortlist_id == shortlist_id,
            ShortlistEntry.player_id == player_id,
        )
        .first()
    )
    if existing is not None:
        if existing.removed_at is None:
            raise DuplicateEntry(
                f"{player.canonical_name} is already in this shortlist."
            )
        # Re-adding a previously-removed player: un-remove, keep full history.
