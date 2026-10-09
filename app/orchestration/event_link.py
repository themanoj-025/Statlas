"""Player-link step for StatsBomb event data (Phase 3).

The weekly refresh ingests events with `player_id` NULL (explicit, logged — the
Phase 1 sync never guessed). This step resolves them against canonical players
using the SAME non-destructive rules as reconciliation.py:

1. Exact normalized-name match against canonical names.
2. Exact normalized-name match against existing `player_name_aliases` rows for
   the statsbomb source (a human-confirmed spelling store).
3. When more than one candidate matches, the event stays unmatched (NULL) and
   the ambiguity is logged — never a silent best-guess join (Constitution §3).

It runs right after the statsbomb sync in run_weekly_refresh and is idempotent:
already-linked events are skipped.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import MatchEvent, Player, PlayerNameAlias
from app.reconciliation import strip_suffixes

logger = logging.getLogger(__name__)


@dataclass
class EventLinkReport:
    events_total: int = 0
    linked: int = 0
    already_linked: int = 0
    unmatched: int = 0
    ambiguous: list[str] = field(default_factory=list)


def link_match_events(db: Session) -> EventLinkReport:
    """Resolve unmatched events to players by exact normalized name.

    Matching is exact-only: an event whose name matches exactly one candidate
    is linked; zero candidates stays unmatched; two or more candidates is
    logged as ambiguous and left NULL (a human reconciliation decision).
    """
    report = EventLinkReport()

    unmatched = db.query(MatchEvent).filter(MatchEvent.player_id.is_(None)).all()
    if not unmatched:
        return report
    report.events_total = len(unmatched)

    # Name indexes built ONCE per run (O(1) lookups per event).
    by_norm_name: dict[str, list[Player]] = {}
    for player in db.query(Player).all():
        by_norm_name.setdefault(strip_suffixes(player.canonical_name), []).append(
            player
        )
    alias_names: dict[str, Player] = {}
    for alias in (
        db.query(PlayerNameAlias).filter(PlayerNameAlias.source == "statsbomb").all()
    ):
        alias_names.setdefault(strip_suffixes(alias.source_name_string), alias.player)

    for event in unmatched:
        raw_name = (event.extra or {}).get("player_name")
        if not raw_name:
            report.unmatched += 1
            continue
        norm = strip_suffixes(raw_name)
        candidates = list(by_norm_name.get(norm, []))
        alias_player = alias_names.get(norm)
        if alias_player is not None and alias_player not in candidates:
            candidates.append(alias_player)
        if len(candidates) == 1:
            event.player_id = candidates[0].id
            report.linked += 1
        elif len(candidates) > 1:
            report.ambiguous.append(norm)
            logger.warning(
                "event player-link: '%s' matches %d players (%s) — left NULL for review",
                raw_name,
                len(candidates),
                ", ".join(p.canonical_name for p in candidates),
            )
            report.unmatched += 1
        else:
            report.unmatched += 1

    db.commit()
    report.already_linked = (
        db.query(MatchEvent.id).filter(MatchEvent.player_id.is_not(None)).count()
    ) - report.linked
    return report
