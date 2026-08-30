"""Workspace entry CRUD operations."""

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

    # Batch-compute slugs only for players in this shortlist (not all players).

    entry_player_map = {pid: db.get(Player, pid) for pid in player_ids}
    entry_teams = {
        pid: db.get(Team, p.current_team_id)
        for pid, p in entry_player_map.items()
        if p and p.current_team_id
    }
    slugs = _compact_slug_map(db, player_ids, entry_player_map, entry_teams) if player_ids else {}

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
