"""Data-driven sentences (Constitution §5, Never-List #4).

Every player page carries at least one unique sentence generated from the
player's REAL published percentile data by this module — never a hardcoded
example, never a fabricated number. Unit tests cover grammar, pluralization,
ranges, and boundary cases (percentile 0, tiny samples, league with zero
qualifying players).

Template (populated from the database):
    "{Name} ranks in the {Nth} percentile for {metric} among {Tier N}
     {position-plural} this season."
plus an index sentence when the player has one:
    "Statlas Index {score}: the weighted average of their percentile ranks."
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import PercentileSnapshot, StatSnapshot
from app.queries.player_queries import (
    get_player_percentiles,
    get_player_profile,
    get_player_raw_stats,
)

TIER_LABELS = {"tier_1": "Tier 1", "tier_2": "Tier 2", "tier_3": "Tier 3"}

POSITION_PLURALS = {
    "GK": "goalkeepers",
    "CB": "centre-backs",
    "FB": "full-backs",
    "DM": "defensive midfielders",
    "CM": "central midfielders",
    "AM": "attacking midfielders",
    "W": "wide attackers",
    "ST": "strikers",
}


def ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 11-13 -> '11th', 21 -> '21st'..."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _tier_and_group(db: Session, player_id: int) -> tuple[str, str] | None:
    row = (
        db.query(PercentileSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            StatSnapshot.player_id == player_id,
        )
        .order_by(StatSnapshot.scrape_date.desc())
        .first()
    )
    if row is None:
        return None
    return row.league_tier, row.position_group


def build_profile_sentence(db: Session, player_id: int) -> str:
    """One (or two) data-driven sentences from real published values.

    Boundary behaviour (all unit-tested):
    - No published percentiles + below threshold -> pending-qualification copy
      with the player's actual minutes (never a fabricated score).
    - No published percentiles + no snapshot at all -> coverage-honest copy.
    - Percentile 0 -> "at the bottom of the group" phrasing (no false precision).
    - Tiny pool / no qualifying players -> the pending-qualification path above.
    """
    profile = get_player_profile(db, player_id)
    if profile is None:
        return ""
    name = profile["name"]

    percentiles = get_player_percentiles(db, player_id)
    raw = get_player_raw_stats(db, player_id)

    if percentiles is None or not percentiles["percentiles"]:
        if raw is not None and raw["minutes_played"] < load_registry()["qualifying_minutes"]:
            minutes = int(raw["minutes_played"])
            return (
                f"{name} is pending qualification this season with {minutes} league "
                f"minutes — percentile ranks resume at the 900-minute threshold."
            )
        if raw is not None:
            return (
                f"{name} has no published percentile ranks for this season yet — "
                f"the weekly refresh publishes them after the anomaly check passes."
            )
        return f"{name} is not in the current data coverage (see the data coverage page)."

    tier_group = _tier_and_group(db, player_id)
    if tier_group is None:
        return f"{name} has no published percentile ranks for this season yet."
    tier, group = tier_group

    registry = load_registry()
    position_plural = POSITION_PLURALS.get(group, "players")
    tier_label = TIER_LABELS.get(tier, tier)

    # Highest percentile among the position's own metrics (never a cross-group
    # metric that happens to be present).
    metric_ids = registry["gk_metrics"] if group == "GK" else registry["outfield_metrics"]
    candidates = [
        (mid, pct)
        for mid, pct in percentiles["percentiles"].items()
        if mid in metric_ids
    ]
    if not candidates:
        return (
            f"{name} has published percentile data but none on this position "
            f"group's metrics this season."
        )
    top_metric, top_pct = max(candidates, key=lambda item: item[1])
    metric_name = registry["metrics"][top_metric]["name"]

    if top_pct < 0.5:
        rank_clause = f"ranks at the bottom of the group for {metric_name}"
    else:
        rank_clause = (
            f"ranks in the {ordinal(round(top_pct))} percentile for {metric_name}"
        )

    sentence = (
        f"{name} {rank_clause} among {tier_label} {position_plural} this season."
    )
    if percentiles["index"] is not None:
        sentence += (
            f" Their Statlas Index is {percentiles['index']:.1f}, the weighted "
            f"average of their percentile ranks."
        )
    return sentence
