"""Player name reconciliation (Constitution §3: name reconciliation is an
explicit mapping step with logged mismatches — never a silent best-guess join).

Matching strategy (from the Phase 1 spec):
1. External-id lookup first (stable FBref/Understat player ids when present).
2. Existing alias lookup (source, source_name_string).
3. Exact match on normalized name (+ normalized team, + approximate DOB year).
4. Anything unmatched goes to the `reconciliation_queue` for a HUMAN decision —
   never a fuzzy guess.
5. A manual resolution writes a permanent row to `player_name_aliases`, so the
   same mismatch never needs resolving again.

Why a separate alias table instead of fuzzy-matching at query time: alias rows
are traceable (who resolved them, when), correctable (delete/redirect the row),
auditable (the queue log exists), and they make joins O(index lookup) instead
of O(n) similarity scans on every query.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Player, PlayerNameAlias, ReconciliationQueue

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")
_SUFFIXES = ("jr", "sr", "ii", "iii", "iv")


def normalize_name(name: str) -> str:
    """Lowercase, strip accents, drop punctuation, collapse whitespace.

    'José Mourinho' -> 'jose mourinho'; 'K. De Bruyne' -> 'k de bruyne'.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = _PUNCT_RE.sub(" ", ascii_only)
    return _WS_RE.sub(" ", cleaned).strip().lower()


def strip_suffixes(name: str) -> str:
    """Remove trailing generation suffixes for comparison: 'Haaland Jr.' -> 'Haaland'."""
    parts = normalize_name(name).split()
    while parts and parts[-1] in _SUFFIXES:
        parts.pop()
    return " ".join(parts)


def normalized_team(team_name: str | None) -> str | None:
    """Team-name normalizer. Kept intentionally conservative — corporate and
    abbreviated club names stay a manual/review concern, not a fuzzy guess."""
    return normalize_name(team_name) if team_name else None


class Reconciler:
    """Index-backed reconciler. Preloads players once per batch, then resolves
    each source record in O(1) lookups (the pipeline sees thousands of records
    per refresh; a per-record full scan would be quadratic)."""

    def __init__(self, db: Session) -> None:
        from app.models import (
            Team,  # local import: only needed for the team tie-breaker
        )

        self.db = db
        self._players = db.query(Player).all()
        self._team_names: dict[int, str] = {t.id: t.name for t in db.query(Team).all()}
        self._by_external: dict[tuple[str, Any], Player] = {}
        self._by_transfermarkt: dict[int, Player] = {}
        self._by_norm_name: dict[str, list[Player]] = {}
        # Iterate a COPY: register_player() appends to self._players (so records
        # created mid-batch resolve against each other), which would otherwise
        # grow the list under the loop forever on a non-empty database.
        for player in list(self._players):
            self.register_player(player)

    def register_player(self, player: Player) -> None:
        """Add a player to the in-memory indexes (used for newly created players
        so later records in the same batch resolve against them)."""
        self._players.append(player)
        for key, value in (player.external_ids or {}).items():
            if value not in (None, "", 0):
                self._by_external[(key, value)] = player
        if player.transfermarkt_id:
            self._by_transfermarkt[player.transfermarkt_id] = player
        norm = strip_suffixes(player.canonical_name)
        self._by_norm_name.setdefault(norm, []).append(player)

    # -- lookup helpers -------------------------------------------------------

    def find_by_transfermarkt_id(self, tm_id: int) -> Player | None:
        """Direct O(1) lookup by Transfermarkt player ID."""
        return self._by_transfermarkt.get(tm_id)

    def find_by_external(self, external_ids: dict[str, Any]) -> Player | None:
        # Fast path: Transfermarkt ID via dedicated index
        tm_id = external_ids.get("transfermarkt") if external_ids else None
        if tm_id:
            player = self._by_transfermarkt.get(int(tm_id))
            if player:
                return player
        # General path: scan external_ids dict
        for key, value in (external_ids or {}).items():
            if value not in (None, "", 0) and (key, value) in self._by_external:
                return self._by_external[(key, value)]
        return None

    def _alias_lookup(self, source: str, source_name: str) -> Player | None:
        alias = (
            self.db.query(PlayerNameAlias)
            .filter_by(source=source, source_name_string=source_name)
            .first()
        )
        return alias.player if alias else None

    def _exact_match(
        self, source_name: str, source_team: str | None, dob_year: int | None
    ) -> Player | None:
        """Exact normalized-name match with two tie-breakers, in priority order:
        (1) DOB year equality, (2) current-team name equality. Neither tie-breaker
        ever blocks a name-only match when the other side has no signal."""
        norm = strip_suffixes(source_name)
        candidates = self._by_norm_name.get(norm, [])
        if not candidates:
            return None

        def player_team_norm(player: Player) -> str | None:
            if player.current_team_id is None:
                return None
            name = self._team_names.get(player.current_team_id)
            return normalized_team(name) if name else None

        def dob_matches(player: Player) -> bool:
            if dob_year is None or player.date_of_birth is None:
                return True  # no DOB signal on either side
            return player.date_of_birth.year == dob_year

        team_norm = normalized_team(source_team)
        pool = [p for p in candidates if dob_matches(p)] or candidates
        if team_norm is not None:
            team_strong = [p for p in pool if player_team_norm(p) == team_norm]
            if team_strong:
                return team_strong[0]
        return pool[0]

    # -- public API -----------------------------------------------------------
    def match_existing(self, record: Any) -> Player | None:
        """The three non-destructive match steps, in order. No queue writes."""
        external_ids = getattr(record, "external_ids", None) or {}
        player = self.find_by_external(external_ids)
        if player is not None:
            return player
        player = self._alias_lookup(record.source, record.player_name)
        if player is not None:
            return player
        return self._exact_match(
            record.player_name,
            getattr(record, "team_name", None),
            getattr(record, "dob_year", None),
        )

    def ensure_alias(self, player: Player, record: Any) -> None:
        exists = (
            self.db.query(PlayerNameAlias)
            .filter_by(
                player_id=player.id,
                source=record.source,
                source_name_string=record.player_name,
            )
            .first()
        )
        if exists is None:
            self.db.add(
                PlayerNameAlias(
                    player_id=player.id,
                    source=record.source,
                    source_name_string=record.player_name,
                )
            )

    def enqueue(self, record: Any, *, note: str | None = None) -> None:
        """Write an unmatched source record to the queue for a human decision."""
        external_ids = getattr(record, "external_ids", None) or {}
        record_key = str(
            external_ids.get("fbref")
            or external_ids.get("understat")
            or record.player_name
        )
        exists = (
            self.db.query(ReconciliationQueue)
            .filter_by(source=record.source, source_record_key=record_key)
            .first()
        )
        if exists is None:
            self.db.add(
                ReconciliationQueue(
                    source=record.source,
                    source_record_key=record_key,
                    source_name=record.player_name,
                    source_team=getattr(record, "team_name", None),
                    status="pending",
                    notes=note
                    or "no external id / alias / exact normalized match; review required",
                )
            )


def resolve_queue_item(
    db: Session,
    queue_id: int,
    player_id: int,
    *,
    note: str | None = None,
    now: datetime | None = None,
) -> ReconciliationQueue -> None:
    """Human-confirmed resolution: link the queued source record to a player and
    write the permanent alias row so the mismatch never recurs."""
    now = now or datetime.now(timezone.utc)
    item = db.get(ReconciliationQueue, queue_id)
    if item is None:
        raise ValueError(f"no reconciliation queue item with id {queue_id}")
    if item.status != "pending":
        raise ValueError(f"queue item {queue_id} is already {item.status}")
    player = db.get(Player, player_id)
    if player is None:
        raise ValueError(f"no player with id {player_id}")

    item.candidate_player_id = player_id
    item.status = "resolved"
    item.resolved_at = now
    item.notes = note or item.notes

    exists = (
        db.query(PlayerNameAlias)
        .filter_by(
            player_id=player_id, source=item.source, source_name_string=item.source_name
        )
        .first()
    )
    if exists is None:
        db.add(
            PlayerNameAlias(
                player_id=player_id,
                source=item.source,
                source_name_string=item.source_name,
            )
        )
    db.commit()
    return item


def list_pending(db: Session) -> list[ReconciliationQueue]:
    return (
        db.query(ReconciliationQueue)
        .filter(ReconciliationQueue.status == "pending")
        .order_by(ReconciliationQueue.id)
        .all()
    )
