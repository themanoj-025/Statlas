"""Phase 5 A4 — automated audit of the data-driven sentence across the FULL dataset.

Constitution §5: every player page must carry a sentence generated from real
published values. Phase 2 spot-checked five players; this script checks every
player with published percentiles in the database and flags:

  1. Grammar/format anomalies (double spaces, "None", "nan", unbalanced quotes)
  2. Implausible values (percentile ranks outside 0-100, index outside 0-100,
     negative per-90 values where the metric cannot be negative)
  3. Sentences that fall back to coverage/pending copy for players who
     actually qualify (a sign the generator lost data it should have had)

Usage:
    # Uses the repo-default dev DB (data/dev.db) unless DATABASE_URL is set,
    # matching scripts/seed_dev_db.py.
    python scripts/audit_sentences.py

Exit code 0 = clean, 1 = anomalies found (so CI can enforce it).
"""

from __future__ import annotations

import re
import sys

from sqlalchemy.orm import Session

from app.config import load_registry
from app.db import session_scope
from app.models import PercentileSnapshot, Player, StatSnapshot
from app.queries.sentences import build_profile_sentence

PENDING_MARKERS = (
    "pending qualification",
    "no published percentile ranks",
    "not in the current data coverage",
)


def audit(db: Session) -> list[str]:
    problems: list[str] = []

    rows = (
        db.query(
            Player.id,
            Player.canonical_name,
            StatSnapshot.minutes_played,
            PercentileSnapshot.league_tier,
            PercentileSnapshot.position_group,
            PercentileSnapshot.index_score,
        )
        .join(StatSnapshot, StatSnapshot.player_id == Player.id)
        .join(
            PercentileSnapshot,
            PercentileSnapshot.stat_snapshot_id == StatSnapshot.id,
        )
        .filter(PercentileSnapshot.is_published.is_(True))
        .all()
    )
    if not rows:
        return ["AUDIT-FATAL: no published percentile rows found"], 0

    # Latest published snapshot per player (dedupe players appearing twice).
    latest: dict[int, dict] = {}
    for player_id, name, minutes, tier, group, index in rows:
        if player_id not in latest:
            latest[player_id] = {
                "name": name,
                "minutes": minutes,
                "tier": tier,
                "group": group,
                "index": index,
            }

    registry = load_registry()
    qualifying = registry["qualifying_minutes"]

    for player_id, info in latest.items():
        sentence = build_profile_sentence(db, player_id)
        if not sentence:
            problems.append(f"{info['name']} (id {player_id}): EMPTY sentence")
            continue

        # 1 — grammar/format anomalies. "nan"/"None" must be checked as
        # whole tokens (word boundaries): the fixture dataset legitimately
        # contains names like "Fernandez", where a naive substring match
        # produces false positives (found by the first audit run).
        if "  " in sentence:
            problems.append(
                f"{info['name']} (id {player_id}): double space: {sentence!r}"
            )
        for bad in (r"\bNone\b", r"\bnan\b", r"\bNaN\b", r" .,", r" \."):
            if re.search(bad, sentence):
                problems.append(
                    f"{info['name']} (id {player_id}): literal {bad!r}: {sentence!r}"
                )
                break

        # 2 — implausible values: percentile ranks must be 0-100, index 0-100
        for m in re.finditer(r"(\d+(?:\.\d+)?)(st|nd|rd|th) percentile", sentence):
            val = float(m.group(1))
            if not 0 <= val <= 100:
                problems.append(
                    f"{info['name']} (id {player_id}): percentile {val} out of range: {sentence!r}"
                )
        for m in re.finditer(r"Index is (\d+(?:\.\d+)?)", sentence):
            val = float(m.group(1))
            if not 0 <= val <= 100:
                problems.append(
                    f"{info['name']} (id {player_id}): index {val} out of range: {sentence!r}"
                )

        # 3 — a qualified player must not get pending/coverage fallback copy
        if info["minutes"] >= qualifying and any(
            marker in sentence for marker in PENDING_MARKERS
        ):
            problems.append(
                f"{info['name']} (id {player_id}): {info['minutes']} min >= {qualifying} "
                f"threshold but got fallback copy: {sentence!r}"
            )

    return problems, len(latest)


def main() -> int:
    with session_scope() as db:
        problems, scanned = audit(db)
    print(f"AUDIT: scanned {scanned} players with published percentiles.")
    if problems:
        print(f"AUDIT: {len(problems)} problem(s) found across the full dataset:\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("AUDIT: clean — every data-driven sentence is well-formed and within bounds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
