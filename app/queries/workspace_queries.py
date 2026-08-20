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
from app.queries.player_queries import player_slug_map

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
        sid: {"entry_count": 0, "status_breakdown": {s: 0 for s in ALL_STATUSES}}
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
        existing.removed_at = None
        existing.updated_at = _now()
        _bump_shortlist(db, shortlist_id)
        db.commit()
        return {"entry_id": existing.id, "status": existing.status}

    note = (initial_note or "").strip() or None
    entry = ShortlistEntry(
        shortlist_id=shortlist_id,
        player_id=player_id,
        status="discovered",
        added_by_note=note,
    )
    db.add(entry)
    db.flush()
    db.add(
        StatusHistory(
            shortlist_entry_id=entry.id,
            from_status=None,
            to_status="discovered",
            changed_by_user_id=user_id,
        )
    )
    _bump_shortlist(db, shortlist_id)
    db.commit()
    return {"entry_id": entry.id, "status": entry.status}


def update_entry_status(
    db: Session,
    user_id: int,
    entry_id: int,
    new_status: str,
    reason_note: str | None = None,
) -> dict[str, Any]:
    """Change an entry's status with pipeline validation + a history row."""
    entry = _owned_entry(db, user_id, entry_id)
    error = validate_transition(entry.status, new_status)
    if error:
        raise InvalidStatusTransition(error)
    if entry.status == new_status:
        return {"entry_id": entry.id, "status": entry.status, "history_written": False}

    db.add(
        StatusHistory(
            shortlist_entry_id=entry.id,
            from_status=entry.status,
            to_status=new_status,
            changed_by_user_id=user_id,
            reason_note=(reason_note or "").strip() or None,
        )
    )
    entry.status = new_status
    entry.updated_at = _now()
    _bump_shortlist(db, entry.shortlist_id)
    db.commit()
    return {"entry_id": entry.id, "status": entry.status, "history_written": True}


def set_entry_priority(
    db: Session, user_id: int, entry_id: int, priority: str | None
) -> dict[str, Any]:
    """Set (or clear, with None) an entry's priority."""
    if priority is not None and priority not in PRIORITIES:
        raise ValueError(
            f"Unknown priority '{priority}' — use low, medium, high, or none."
        )
    entry = _owned_entry(db, user_id, entry_id)
    entry.priority = priority
    entry.updated_at = _now()
    _bump_shortlist(db, entry.shortlist_id)
    db.commit()
    return {"entry_id": entry.id, "priority": entry.priority}


def add_entry_note(
    db: Session, user_id: int, entry_id: int, note_text: str
) -> dict[str, Any]:
    """Append a timestamped note to an entry (never overwrites earlier ones)."""
    note_text = (note_text or "").strip()
    if not note_text:
        raise ValueError("A note needs some text.")
    if len(note_text) > 4000:
        raise ValueError("Notes are limited to 4000 characters.")
    entry = _owned_entry(db, user_id, entry_id)
    note = EntryNote(
        shortlist_entry_id=entry.id,
        author_user_id=user_id,
        note_text=note_text,
    )
    db.add(note)
    entry.updated_at = _now()
    _bump_shortlist(db, entry.shortlist_id)
    db.commit()
    return {"note_id": note.id, "created_at": note.created_at.isoformat()}


def add_entry_tag(
    db: Session, user_id: int, entry_id: int, tag_text: str
) -> dict[str, Any]:
    """Add a tag (normalized lowercase). Adding an existing tag is a no-op —
    idempotent by design so a double-click on a suggestion never errors."""
    tag_text = (tag_text or "").strip().lower()
    if not tag_text:
        raise ValueError("A tag needs some text.")
    if len(tag_text) > 64:
        raise ValueError("Tags are limited to 64 characters.")
    entry = _owned_entry(db, user_id, entry_id)
    existing = (
        db.query(EntryTag)
        .filter(EntryTag.shortlist_entry_id == entry.id, EntryTag.tag_text == tag_text)
        .first()
    )
    if existing is None:
        db.add(EntryTag(shortlist_entry_id=entry.id, tag_text=tag_text))
        _bump_shortlist(db, entry.shortlist_id)
        db.commit()
    return {"tag": tag_text}


def remove_entry_tag(db: Session, user_id: int, entry_id: int, tag_text: str) -> None:
    """Remove a tag (tags are vocabulary, not audit data — hard delete is fine)."""
    entry = _owned_entry(db, user_id, entry_id)
    db.query(EntryTag).filter(
        EntryTag.shortlist_entry_id == entry.id,
        EntryTag.tag_text == (tag_text or "").strip().lower(),
    ).delete()
    _bump_shortlist(db, entry.shortlist_id)
    db.commit()


def remove_entry(db: Session, user_id: int, shortlist_id: int, player_id: int) -> None:
    """Soft-delete an entry: removed_at set, notes/tags/status_history intact."""
    _owned_shortlist(db, user_id, shortlist_id)
    entry = (
        db.query(ShortlistEntry)
        .filter(
            ShortlistEntry.shortlist_id == shortlist_id,
            ShortlistEntry.player_id == player_id,
            ShortlistEntry.removed_at.is_(None),
        )
        .first()
    )
    if entry is None:
        raise ShortlistNotFound(
            f"no active entry for player {player_id} in shortlist {shortlist_id}"
        )
    entry.removed_at = _now()
    _bump_shortlist(db, shortlist_id)
    db.commit()


def remove_entry_by_id(db: Session, user_id: int, entry_id: int) -> None:
    """Soft-delete by entry id (API convenience; same audit semantics)."""
    entry = _owned_entry(db, user_id, entry_id)
    entry.removed_at = _now()
    _bump_shortlist(db, entry.shortlist_id)
    db.commit()


# ---------------------------------------------------------------------------
# Detail + memberships
# ---------------------------------------------------------------------------


def get_shortlist_memberships(db: Session, user_id: int, player_id: int) -> list[int]:
    """Shortlist ids (non-deleted) that currently contain the player — used by
    the Add-to-Shortlist UI to mark existing memberships."""
    rows = (
        db.query(Shortlist.id)
        .join(ShortlistEntry, ShortlistEntry.shortlist_id == Shortlist.id)
        .filter(
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            ShortlistEntry.player_id == player_id,
            ShortlistEntry.removed_at.is_(None),
        )
        .all()
    )
    return [row[0] for row in rows]


def get_shortlist_detail(
    db: Session, user_id: int, shortlist_id: int
) -> dict[str, Any]:
    """One shortlist with all entries joined to player summary data.

    Deliberately NOT an N+1 per entry: entry/player/team/league come from one
    join, the latest published index percentile in one grouped query, and
    notes/tags/history in one query each — a handful of queries total no
    matter how many entries the shortlist holds.
    """
    shortlist = _owned_shortlist(db, user_id, shortlist_id)

    rows = (
        db.query(ShortlistEntry, Player, Team, League)
        .join(Player, ShortlistEntry.player_id == Player.id)
        .outerjoin(Team, Player.current_team_id == Team.id)
        .outerjoin(League, Team.league_id == League.id)
        .filter(
            ShortlistEntry.shortlist_id == shortlist_id,
            ShortlistEntry.removed_at.is_(None),
        )
        .order_by(ShortlistEntry.added_at.desc(), ShortlistEntry.id.desc())
        .all()
    )

    # Latest published index percentile per player (single grouped query).
    player_ids = [entry.player_id for entry, *_ in rows]
    index_by_player: dict[int, dict[str, Any]] = {}
    if player_ids:
        index_id = load_registry()["index_metric_id"]
        percentile_rows = (
            db.query(PercentileSnapshot, StatSnapshot)
            .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
            .filter(
                StatSnapshot.player_id.in_(player_ids),
                PercentileSnapshot.metric_name == index_id,
                PercentileSnapshot.is_published.is_(True),
            )
            .order_by(StatSnapshot.scrape_date.desc(), PercentileSnapshot.id.desc())
            .all()
        )
        # Latest scrape per player (mirrors get_player_percentiles semantics).
        for percentile, snap in percentile_rows:
            if snap.player_id not in index_by_player:
                index_by_player[snap.player_id] = {
                    "index": percentile.index_score,
                    "snapshot_date": snap.scrape_date,
                }

    slugs = {p["player_id"]: p["slug"] for p in player_slug_map(db)}

    entry_ids = [entry.id for entry, *_ in rows]
    notes_by_entry: dict[int, list[dict[str, Any]]] = {}
    tags_by_entry: dict[int, list[str]] = {}
    history_by_entry: dict[int, list[dict[str, Any]]] = {}
    if entry_ids:
        for note in (
            db.query(EntryNote)
            .filter(EntryNote.shortlist_entry_id.in_(entry_ids))
            .order_by(EntryNote.created_at.desc(), EntryNote.id.desc())
            .all()
        ):
            notes_by_entry.setdefault(note.shortlist_entry_id, []).append(
                {
                    "id": note.id,
                    "author_user_id": note.author_user_id,
                    "note_text": note.note_text,
                    "created_at": note.created_at.isoformat(),
                }
            )
        for tag in (
            db.query(EntryTag)
            .filter(EntryTag.shortlist_entry_id.in_(entry_ids))
            .order_by(EntryTag.tag_text.asc())
            .all()
        ):
            tags_by_entry.setdefault(tag.shortlist_entry_id, []).append(tag.tag_text)
        for h in (
            db.query(StatusHistory)
            .filter(StatusHistory.shortlist_entry_id.in_(entry_ids))
            .order_by(StatusHistory.changed_at.desc(), StatusHistory.id.desc())
            .all()
        ):
            history_by_entry.setdefault(h.shortlist_entry_id, []).append(
                {
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "changed_by_user_id": h.changed_by_user_id,
                    "changed_at": h.changed_at.isoformat(),
                    "reason_note": h.reason_note,
                }
            )

    entries = []
    for entry, player, team, league in rows:
        idx = index_by_player.get(player.id, {})
        entries.append(
            {
                "entry_id": entry.id,
                "player_id": player.id,
                "name": player.canonical_name,
                "slug": slugs.get(player.id),
                "position_group": player.position_group,
                "position_label": player.primary_position,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "index": idx.get("index"),
                "snapshot_date": (
                    idx["snapshot_date"].isoformat() if "snapshot_date" in idx else None
                ),
                "status": entry.status,
                "priority": entry.priority,
                "added_at": entry.added_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "added_by_note": entry.added_by_note,
                "notes": notes_by_entry.get(entry.id, []),
                "tags": tags_by_entry.get(entry.id, []),
                "status_history": history_by_entry.get(entry.id, []),
            }
        )

    counts = _entry_counts(db, [shortlist_id])[shortlist_id]
    return {
        "shortlist_id": shortlist.id,
        "name": shortlist.name,
        "description": shortlist.description,
        "created_at": shortlist.created_at.isoformat(),
        "updated_at": shortlist.updated_at.isoformat(),
        "entries": entries,
        "entry_count": counts["entry_count"],
        "status_breakdown": counts["status_breakdown"],
    }


def get_user_tag_suggestions(
    db: Session, user_id: int, prefix: str, limit: int = 10
) -> list[str]:
    """Most-used tags from the user's OWN shortlists, for autocomplete. Never
    another user's private vocabulary (privacy/authorization, scouting-
    pipeline.md §4)."""
    prefix = (prefix or "").strip().lower()
    query = (
        db.query(EntryTag.tag_text, func.count(EntryTag.id))
        .join(ShortlistEntry, EntryTag.shortlist_entry_id == ShortlistEntry.id)
        .join(Shortlist, ShortlistEntry.shortlist_id == Shortlist.id)
        .filter(
            Shortlist.user_id == user_id,
            Shortlist.deleted_at.is_(None),
            ShortlistEntry.removed_at.is_(None),
        )
    )
    if prefix:
        query = query.filter(EntryTag.tag_text.like(f"{prefix}%"))
    rows = (
        query.group_by(EntryTag.tag_text)
        .order_by(func.count(EntryTag.id).desc(), EntryTag.tag_text.asc())
        .limit(limit)
        .all()
    )
    return [tag for tag, _count in rows]
