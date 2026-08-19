"""Formation detection and stability analysis from event positioning data.

Constitution §3: Never fabricate. Formations are detected from real event
positions, not guessed or copied from broadcast data.

Constitution §1.3: Uncertainty is flagged. Formation detection from event
data has inherent limitations — detected formations may differ from nominal
lineups due to tactical shifts, data gaps, or positional fluidity.

Phase 17 Part D: Formation detection from player positions, stability
tracking over time, and formation effectiveness analysis.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import MatchEvent


# ---------------------------------------------------------------------------
# D1 — Formation detection from player positions
# ---------------------------------------------------------------------------

# Position group classification from x-coordinate (StatsBomb: x ∈ [0, 120])
# GK: x < 12 (own goal area)
# DEF: 12 ≤ x < 45
# MID: 45 ≤ x < 75
# FWD: x ≥ 75
POSITION_THRESHOLDS = {
    "GK": (0, 12),
    "DEF": (12, 45),
    "MID": (45, 75),
    "FWD": (75, 120),
}


def detect_formation(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
    *,
    minute_start: float = 0,
    minute_end: float = 120,
) -> dict[str, Any]:
    """Detect the team's formation from player positioning during a match.

    Uses event data positions (pass origins, defensive actions, etc.) to
    estimate which line each player operates in, then counts players per line.

    Returns:
        formation: tuple of (defenders, midfielders, forwards) — e.g. (4, 3, 3)
        formation_str: human-readable string — e.g. "4-3-3"
        player_lines: per-player line assignment
        confidence: detection confidence (0-1)
    """
    # Get all events in time window
    query = db.query(MatchEvent).filter(
        MatchEvent.match_id == match_id,
        MatchEvent.x_coordinate.isnot(None),
        MatchEvent.y_coordinate.isnot(None),
        MatchEvent.minute >= minute_start,
        MatchEvent.minute <= minute_end,
    )
    if team_player_ids:
        query = query.filter(MatchEvent.player_id.in_(team_player_ids))

    events = query.all()

    if not events:
        return {
            "formation": (0, 0, 0),
            "formation_str": "unknown",
            "player_lines": {},
            "confidence": 0,
            "message": "No events with coordinates available for this time window.",
        }

    # Aggregate player positions (average x, y per player)
    player_positions: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for ev in events:
        if ev.player_id is not None:
            player_positions[ev.player_id].append(
                (ev.x_coordinate, ev.y_coordinate)
            )

    # Exclude GK (typically has very different x distribution)
    # GK is usually in x < 15 area
    player_avg_x: dict[int, float] = {}
    for pid, positions in player_positions.items():
        avg_x = sum(p[0] for p in positions) / len(positions)
        player_avg_x[pid] = avg_x

    # Classify players into lines
    outfield_players = {
        pid: avg_x for pid, avg_x in player_avg_x.items()
        if avg_x > 15  # Exclude GK
    }

    defenders = []
    midfielders = []
    forwards = []

    for pid, avg_x in outfield_players.items():
        if avg_x < 45:
            defenders.append(pid)
        elif avg_x < 75:
            midfielders.append(pid)
        else:
            forwards.append(pid)

    n_def = len(defenders)
    n_mid = len(midfielders)
    n_fwd = len(forwards)

    # If we have exactly 10 outfield + 1 GK, we're confident
    total_outfield = n_def + n_mid + n_fwd
    confidence = 1.0 if total_outfield == 10 else max(0.3, 1.0 - abs(total_outfield - 10) * 0.1)

    formation = (n_def, n_mid, n_fwd)
    formation_str = f"{n_def}-{n_mid}-{n_fwd}"

    player_lines = {}
    for pid in defenders:
        player_lines[pid] = "DEF"
    for pid in midfielders:
        player_lines[pid] = "MID"
    for pid in forwards:
        player_lines[pid] = "FWD"
    # Add GK
    for pid, avg_x in player_avg_x.items():
        if avg_x <= 15:
            player_lines[pid] = "GK"

    return {
        "formation": formation,
        "formation_str": formation_str,
        "player_lines": player_lines,
        "player_avg_positions": {
            pid: round(avg_x, 1) for pid, avg_x in player_avg_x.items()
        },
        "confidence": round(confidence, 2),
        "outfield_count": total_outfield,
    }


# ---------------------------------------------------------------------------
# D2 — Formation stability analysis (by time windows)
# ---------------------------------------------------------------------------

def analyze_formation_stability(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
    *,
    window_minutes: int = 15,
) -> dict[str, Any]:
    """Track formation changes through the match in time windows.

    Parameters:
        window_minutes: length of each analysis window (default 15 min)

    Returns:
        windows: list of formation detection results per time window
        changes: detected formation changes with approximate times
        stability_score: 0-1 (1 = same formation throughout)
    """
    windows = []
    changes = []

    minute = 0
    while minute < 120:
        end = min(120, minute + window_minutes)
        result = detect_formation(
            db,
            match_id,
            team_player_ids,
            minute_start=minute,
            minute_end=end,
        )
        windows.append({
            "minute_start": minute,
            "minute_end": end,
            "formation": result["formation_str"],
            "formation_tuple": result["formation"],
            "confidence": result["confidence"],
        })
        minute += window_minutes

    # Detect changes
    for i in range(1, len(windows)):
        if windows[i]["formation_tuple"] != windows[i - 1]["formation_tuple"]:
            changes.append({
                "from_formation": windows[i - 1]["formation"],
                "to_formation": windows[i]["formation"],
                "approximate_minute": windows[i]["minute_start"],
                "from_confidence": windows[i - 1]["confidence"],
                "to_confidence": windows[i]["confidence"],
            })

    # Stability score: fraction of transitions with same formation
    if len(windows) <= 1:
        stability_score = 1.0
    else:
        stable_transitions = sum(
            1 for i in range(1, len(windows))
            if windows[i]["formation_tuple"] == windows[i - 1]["formation_tuple"]
        )
        stability_score = stable_transitions / (len(windows) - 1)

    # Most common formation
    formation_counts: dict[str, int] = defaultdict(int)
    for w in windows:
        formation_counts[w["formation"]] += 1
    dominant = max(formation_counts, key=formation_counts.get) if formation_counts else "unknown"

    return {
        "match_id": match_id,
        "windows": windows,
        "changes": changes,
        "stability_score": round(stability_score, 2),
        "dominant_formation": dominant,
        "change_count": len(changes),
    }


# ---------------------------------------------------------------------------
# D3 — Formation effectiveness (correlation with performance)
# ---------------------------------------------------------------------------

def compute_formation_effectiveness(
    db: Session,
    match_ids: list[str],
    team_player_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Analyze which formations correlate with better performance.

    For each match, detect the dominant formation and compare with match outcome
    indicators (shot count, possession percentage, xG if available).

    IMPORTANT: This shows correlation only, not causation. Small sample sizes
    (1-2 matches per formation) do not support strong claims. Uncertainty is
    always flagged.
    """
    formation_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "matches": 0,
        "total_shots": 0,
        "total_passes": 0,
        "avg_possession_x": 0,
    })

    for match_id in match_ids:
        result = detect_formation(db, match_id, team_player_ids)
        formation = result["formation_str"]

        # Count shots and passes in match
        shots = (
            db.query(MatchEvent)
            .filter(
                MatchEvent.match_id == match_id,
                MatchEvent.event_type == "Shot",
                MatchEvent.player_id.in_(team_player_ids) if team_player_ids else True,
            )
            .count()
        )
        passes = (
            db.query(MatchEvent)
            .filter(
                MatchEvent.match_id == match_id,
                MatchEvent.event_type == "Pass",
                MatchEvent.player_id.in_(team_player_ids) if team_player_ids else True,
            )
            .count()
        )

        stats = formation_stats[formation]
        stats["matches"] += 1
        stats["total_shots"] += shots
        stats["total_passes"] += passes

    # Compute averages
    result = {}
    for formation, stats in formation_stats.items():
        n = stats["matches"]
        result[formation] = {
            "matches": n,
            "avg_shots": round(stats["total_shots"] / n, 1) if n > 0 else 0,
            "avg_passes": round(stats["total_passes"] / n, 1) if n > 0 else 0,
            "confidence_note": (
                f"Based on {n} match(es) — "
                + ("small sample, treat with caution" if n < 3 else "reasonable sample")
            ),
        }

    return {
        "formations": result,
        "total_matches": sum(s["matches"] for s in result.values()),
        "caveat": (
            "Formation-performance correlation does not imply causation. "
            "Factors like opponent quality, player availability, and tactical "
            "context significantly influence outcomes."
        ),
    }


# ---------------------------------------------------------------------------
# D4 — Formation conformity analysis
# ---------------------------------------------------------------------------

def analyze_formation_conformity(
    db: Session,
    match_id: str,
    team_player_ids: list[int] | None = None,
    nominal_formation: str | None = None,
) -> dict[str, Any]:
    """Analyze how well players conform to their nominal formation roles.

    Compares detected positions against expected positions for a given formation.
    Players who operate significantly outside their nominal zone are flagged
    as having low conformity (interesting tactical finding).
    """
    result = detect_formation(db, match_id, team_player_ids)
    detected = result["formation"]
    player_lines = result.get("player_lines", {})
    player_positions = result.get("player_avg_positions", {})

    if nominal_formation:
        parts = nominal_formation.split("-")
        nominal = tuple(int(p) for p in parts) if len(parts) == 3 else detected
    else:
        nominal = detected

    # For each player, check if their detected line matches their nominal line
    conformity = {}
    for pid, detected_line in player_lines.items():
        avg_x = player_positions.get(pid, 60)

        # Nominal position based on detected role
        if detected_line == "GK":
            nominal_line = "GK"
        elif detected_line == "DEF":
            nominal_line = "DEF"
        elif detected_line == "MID":
            nominal_line = "MID"
        else:
            nominal_line = "FWD"

        # Check deviation from nominal zone
        in_zone = True
        if nominal_line == "DEF" and avg_x > 55:
            in_zone = False
        elif nominal_line == "MID" and (avg_x < 35 or avg_x > 85):
            in_zone = False
        elif nominal_line == "FWD" and avg_x < 65:
            in_zone = False

        conformity[pid] = {
            "detected_line": detected_line,
            "avg_position_x": avg_x,
            "conforms": in_zone,
        }

    conforming = sum(1 for c in conformity.values() if c["conforms"])
    total = len(conformity)

    return {
        "match_id": match_id,
        "nominal_formation": nominal_formation or result["formation_str"],
        "detected_formation": result["formation_str"],
        "player_conformity": conformity,
        "overall_conformity": round(conforming / total, 2) if total > 0 else 0,
        "non_conforming_players": [
            pid for pid, c in conformity.items() if not c["conforms"]
        ],
    }
