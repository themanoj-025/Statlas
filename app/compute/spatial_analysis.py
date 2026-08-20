"""Pitch zone system, pressure/possession heatmaps, spatial analysis.

Constitution §3: Never fabricate. All heatmaps computed from real event data.
Constitution §1.3: Every recommendation must be explainable.

Phase 17 Part C: Divide pitch into zones for analysis, compute pressure/
defensive density, possession density, and pressure success rate per zone.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import MatchEvent

# ---------------------------------------------------------------------------
# C1 — Pitch zone definitions (StatsBomb 120x80 coordinate system)
# ---------------------------------------------------------------------------

# Standard thirds
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0

# Fine-grained 12-zone grid (3 width × 4 length)
ZONE_COLS = 3  # left, center, right
ZONE_ROWS = 4  # defensive, mid-defensive, mid-attacking, attacking

# Named zones (row, col) → label
ZONE_NAMES = {
    (0, 0): "defensive_left",
    (0, 1): "defensive_center",
    (0, 2): "defensive_right",
    (1, 0): "mid_defensive_left",
    (1, 1): "mid_defensive_center",
    (1, 2): "mid_defensive_right",
    (2, 0): "mid_attacking_left",
    (2, 1): "mid_attacking_center",
    (2, 2): "mid_attacking_right",
    (3, 0): "attacking_left",
    (3, 1): "attacking_center",
    (3, 2): "attacking_right",
}

# Thirds labels
THIRD_NAMES = {0: "defensive", 1: "middle", 2: "attacking"}
WIDTH_NAMES = {0: "left", 1: "center", 2: "right"}


def assign_zone(x: float, y: float) -> tuple[int, int]:
    """Assign a pitch coordinate to a (row, col) zone in the 4×3 grid.

    StatsBomb coordinates: x ∈ [0, 120], y ∈ [0, 80].
    Row 0 = defensive third (x 0-30), Row 3 = attacking third (x 90-120).
    Col 0 = left flank (y 0-27), Col 2 = right flank (y 53-80).
    """
    row = min(ZONE_ROWS - 1, max(0, int(x / (PITCH_LENGTH / ZONE_ROWS))))
    col = min(ZONE_COLS - 1, max(0, int(y / (PITCH_WIDTH / ZONE_COLS))))
    return (row, col)


def assign_zone_name(x: float, y: float) -> str:
    """Return the human-readable zone name for a coordinate."""
    row, col = assign_zone(x, y)
    return ZONE_NAMES.get((row, col), "unknown")


def assign_third(x: float) -> str:
    """Return the third (defensive/middle/attacking) for a coordinate."""
    col = min(2, int(x / (PITCH_LENGTH / 3)))
    return THIRD_NAMES[col]


def assign_width(y: float) -> str:
    """Return the width zone (left/center/right) for a coordinate."""
    col = min(2, int(y / (PITCH_WIDTH / ZONE_COLS)))
    return WIDTH_NAMES[col]


# ---------------------------------------------------------------------------
# C2 — Pressure/defensive action heatmap
# ---------------------------------------------------------------------------


def compute_pressure_heatmap(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Compute defensive/pressure action density per zone.

    Defensive actions: Tackle, Interception, Pressure, Block, Foul Committed.
    Returns zone densities (fraction of total per zone) and per-player breakdown.
    """
    defensive_types = {"Tackle", "Interception", "Pressure", "Block", "Foul Committed"}

    query = db.query(MatchEvent).filter(
        MatchEvent.match_id == match_id,
        MatchEvent.event_type.in_(defensive_types),
    )
    if team_player_ids:
        query = query.filter(MatchEvent.player_id.in_(team_player_ids))

    events = query.all()

    zone_counts: dict[str, int] = defaultdict(int)
    player_zone_counts: dict[int, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    total = 0

    for ev in events:
        if ev.x_coordinate is None or ev.y_coordinate is None:
            continue
        zone = assign_zone_name(ev.x_coordinate, ev.y_coordinate)
        zone_counts[zone] += 1
        total += 1
        if ev.player_id is not None:
            player_zone_counts[ev.player_id][zone] += 1

    # Normalize to densities (fraction of total)
    zone_densities = {
        zone: round(count / total, 4) if total > 0 else 0
        for zone, count in zone_counts.items()
    }

    # Fill missing zones with 0
    all_zones = list(ZONE_NAMES.values())
    for zone in all_zones:
        if zone not in zone_densities:
            zone_densities[zone] = 0

    return {
        "match_id": match_id,
        "type": "pressure",
        "total_actions": total,
        "zone_densities": zone_densities,
        "player_breakdown": {
            pid: dict(zones) for pid, zones in player_zone_counts.items()
        },
    }


# ---------------------------------------------------------------------------
# C3 — Possession density map
# ---------------------------------------------------------------------------


def compute_possession_heatmap(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Compute possession/pass density per zone.

    Possession events: completed Pass and Ball Receipt events.
    Returns zone densities and per-player breakdown.
    """
    possession_types = {"Pass", "Ball Receipt*"}

    query = db.query(MatchEvent).filter(
        MatchEvent.match_id == match_id,
        MatchEvent.event_type.in_(possession_types),
    )
    if team_player_ids:
        query = query.filter(MatchEvent.player_id.in_(team_player_ids))

    events = query.all()

    zone_counts: dict[str, int] = defaultdict(int)
    player_zone_counts: dict[int, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    total = 0

    for ev in events:
        if ev.x_coordinate is None or ev.y_coordinate is None:
            continue
        zone = assign_zone_name(ev.x_coordinate, ev.y_coordinate)
        zone_counts[zone] += 1
        total += 1
        if ev.player_id is not None:
            player_zone_counts[ev.player_id][zone] += 1

    # Normalize to densities
    zone_densities = {
        zone: round(count / total, 4) if total > 0 else 0
        for zone, count in zone_counts.items()
    }

    all_zones = list(ZONE_NAMES.values())
    for zone in all_zones:
        if zone not in zone_densities:
            zone_densities[zone] = 0

    return {
        "match_id": match_id,
        "type": "possession",
        "total_actions": total,
        "zone_densities": zone_densities,
        "player_breakdown": {
            pid: dict(zones) for pid, zones in player_zone_counts.items()
        },
    }


# ---------------------------------------------------------------------------
# C4 — Pressure success rate per zone
# ---------------------------------------------------------------------------


def compute_pressure_success(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Compute pressure success rate per zone.

    "Pressure success" is defined as: a defensive action (pressure/tackle/
    interception) followed by the team regaining possession within 3 events.

    This is a documented approximation — not a precise turnover metric.
    """
    # Get all events in match ordered by sequence
    all_events = (
        db.query(MatchEvent)
        .filter(MatchEvent.match_id == match_id)
        .order_by(MatchEvent.id)
        .all()
    )

    if team_player_ids is None:
        # Infer team from event player_ids
        team_player_ids = list(
            {ev.player_id for ev in all_events if ev.player_id is not None}
        )

    team_set = set(team_player_ids)
    defensive_types = {"Tackle", "Interception", "Pressure", "Block"}

    # Track events for success determination
    event_list = [(ev, ev.player_id, ev.event_type) for ev in all_events]

    zone_success: dict[str, dict[str, int]] = defaultdict(
        lambda: {"success": 0, "total": 0}
    )

    for idx, (ev, player_id, event_type) in enumerate(event_list):
        if event_type not in defensive_types:
            continue
        if player_id not in team_set:
            continue
        if ev.x_coordinate is None or ev.y_coordinate is None:
            continue

        zone = assign_zone_name(ev.x_coordinate, ev.y_coordinate)
        zone_success[zone]["total"] += 1

        # Check if team regains possession within next 3 events
        for future_idx in range(idx + 1, min(idx + 4, len(event_list))):
            future_ev, future_pid, future_type = event_list[future_idx]
            if future_pid in team_set and future_type in ("Pass", "Ball Receipt*"):
                zone_success[zone]["success"] += 1
                break
            if future_type in ("Shot", "Duel Won") and future_pid in team_set:
                zone_success[zone]["success"] += 1
                break

    # Compute rates
    zone_rates = {}
    for zone, counts in zone_success.items():
        rate = counts["success"] / counts["total"] if counts["total"] > 0 else 0
        zone_rates[zone] = {
            "success_rate": round(rate, 3),
            "total_pressures": counts["total"],
            "successful": counts["success"],
        }

    # Fill missing zones
    for zone in ZONE_NAMES.values():
        if zone not in zone_rates:
            zone_rates[zone] = {
                "success_rate": 0,
                "total_pressures": 0,
                "successful": 0,
            }

    return {
        "match_id": match_id,
        "zone_success_rates": zone_rates,
    }


# ---------------------------------------------------------------------------
# Utility — get match coverage check for tactical data
# ---------------------------------------------------------------------------


def has_tactical_data(
    db: Session,
    match_id: str,
    *,
    min_events: int = 100,
) -> dict[str, Any]:
    """Check if a match has sufficient event data for tactical analysis.

    Returns:
        has_coverage: bool
        event_count: int
        message: str
    """

    event_count = db.query(MatchEvent).filter(MatchEvent.match_id == match_id).count()

    if event_count < min_events:
        return {
            "has_coverage": False,
            "event_count": event_count,
            "message": (
                f"Only {event_count} events available for match {match_id}. "
                f"Minimum {min_events} events required for tactical analysis."
            ),
        }

    # Check if any events have coordinates
    coord_count = (
        db.query(MatchEvent)
        .filter(
            MatchEvent.match_id == match_id,
            MatchEvent.x_coordinate.isnot(None),
            MatchEvent.y_coordinate.isnot(None),
        )
        .count()
    )

    if coord_count < min_events:
        return {
            "has_coverage": False,
            "event_count": event_count,
            "message": (
                f"Only {coord_count} events with coordinates available. "
                f"Minimum {min_events} required for spatial analysis."
            ),
        }

    return {
        "has_coverage": True,
        "event_count": event_count,
        "message": f"Sufficient data: {event_count} events, {coord_count} with coordinates.",
    }
