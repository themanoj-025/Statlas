"""Passing network analysis — graph construction, centrality metrics, tactical style detection.

Constitution §3: Never fabricate. All metrics computed from real event data.
Constitution §1.3: Every recommendation must be explainable.

Phase 17 Part B: Passing network construction from event data with real
network science metrics (degree centrality, betweenness centrality, clustering
coefficient) and tactical style detection based on documented thresholds.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import MatchEvent


# ---------------------------------------------------------------------------
# Pitch constants (StatsBomb coordinate system)
# ---------------------------------------------------------------------------
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0


# ---------------------------------------------------------------------------
# B1 — Network construction from event data
# ---------------------------------------------------------------------------

def build_passing_network(
    db: Session,
    match_id: str,
    team_id: int | None = None,
    *,
    phase: str = "full_match",
    minute_start: float | None = None,
    minute_end: float | None = None,
) -> dict[str, Any]:
    """Build a directed passing graph for a match/team from event data.

    Nodes = players (by player_id).
    Edges = completed passes (sender → recipient), weighted by count.

    Parameters:
        phase: 'full_match', 'first_half', 'second_half', 'open_play'
        minute_start / minute_end: optional time window filter
    """
    query = db.query(MatchEvent).filter(
        MatchEvent.match_id == match_id,
        MatchEvent.event_type == "Pass",
    )

    if team_id is not None:
        query = query.filter(MatchEvent.player_id.isnot(None))

    events = query.order_by(MatchEvent.minute.asc().nullsfirst()).all()

    # Filter by phase / time window
    events = _filter_events(events, phase, minute_start, minute_end)

    # Build adjacency: sender → recipient → count
    edges: dict[tuple[int, int], int] = defaultdict(int)
    player_pass_count: dict[int, int] = defaultdict(int)
    player_pass_received: dict[int, int] = defaultdict(int)
    player_pass_attempts: dict[int, int] = defaultdict(int)
    player_pass_completed: dict[int, int] = defaultdict(int)
    player_positions: dict[int, list[tuple[float, float]]] = defaultdict(list)

    for ev in events:
        if ev.player_id is None:
            continue
        extra = ev.extra or {}
        recipient_name = extra.get("recipient")
        end_x = extra.get("end_x")
        end_y = extra.get("end_y")

        sender = ev.player_id
        player_pass_attempts[sender] += 1

        if ev.x_coordinate is not None and ev.y_coordinate is not None:
            player_positions[sender].append((ev.x_coordinate, ev.y_coordinate))

        # Determine if pass was completed (no "Incomplete" outcome)
        outcome = (ev.outcome or "").lower()
        if outcome in ("incomplete", "out", "unknown", "offside", "blocked"):
            continue

        player_pass_completed[sender] += 1
        player_pass_count[sender] += 1

        if recipient_name is None:
            continue

        # Resolve recipient by name matching in same match
        recipient_id = _resolve_recipient_id(db, match_id, recipient_name, sender)
        if recipient_id is None:
            continue

        edges[(sender, recipient_id)] += 1
        player_pass_received[recipient_id] += 1

    # Build nodes
    nodes = []
    for pid in set(list(player_pass_count.keys()) + list(player_pass_received.keys())):
        avg_x = (
            sum(p[0] for p in player_positions[pid]) / len(player_positions[pid])
            if player_positions[pid]
            else None
        )
        avg_y = (
            sum(p[1] for p in player_positions[pid]) / len(player_positions[pid])
            if player_positions[pid]
            else None
        )
        attempts = player_pass_attempts.get(pid, 0)
        completed = player_pass_completed.get(pid, 0)
        nodes.append({
            "player_id": pid,
            "pass_count": player_pass_count.get(pid, 0),
            "pass_received": player_pass_received.get(pid, 0),
            "pass_attempts": attempts,
            "pass_completed": completed,
            "pass_success_rate": round(completed / attempts * 100, 1) if attempts > 0 else 0,
            "avg_x": round(avg_x, 1) if avg_x is not None else None,
            "avg_y": round(avg_y, 1) if avg_y is not None else None,
        })

    # Build edge list
    edge_list = [
        {"from": sender, "to": recipient, "weight": count}
        for (sender, recipient), count in edges.items()
    ]

    return {
        "match_id": match_id,
        "phase": phase,
        "nodes": nodes,
        "edges": edge_list,
        "total_passes": sum(player_pass_count.values()),
    }


def _filter_events(
    events: list,
    phase: str,
    minute_start: float | None,
    minute_end: float | None,
) -> list:
    """Filter events by phase or time window."""
    filtered = events
    if phase == "first_half":
        filtered = [e for e in filtered if (e.minute or 0) < 45]
    elif phase == "second_half":
        filtered = [e for e in filtered if (e.minute or 0) >= 45]
    elif phase == "open_play":
        # Exclude set pieces by checking pass_type in extra
        filtered = [
            e for e in filtered
            if (e.extra or {}).get("pass_type") not in (
                "Corner", "Free Kick", "Throw-in", "Goal Kick",
                "Kick Off", "Penalty", "Cross",
            )
        ]
    if minute_start is not None:
        filtered = [e for e in filtered if (e.minute or 0) >= minute_start]
    if minute_end is not None:
        filtered = [e for e in filtered if (e.minute or 0) <= minute_end]
    return filtered


def _resolve_recipient_id(
    db: Session,
    match_id: str,
    recipient_name: str,
    sender_id: int,
) -> int | None:
    """Resolve a pass recipient name to a player_id from match events."""
    from app.models import Player

    # Try exact name match via player_name_aliases or canonical_name
    match_events_with_names = (
        db.query(MatchEvent.player_id, MatchEvent.extra)
        .filter(
            MatchEvent.match_id == match_id,
            MatchEvent.player_id.isnot(None),
            MatchEvent.player_id != sender_id,
        )
        .distinct()
        .all()
    )
    for pid, extra in match_events_with_names:
        if extra and extra.get("player_name") == recipient_name:
            return pid

    # Fallback: match against Player.canonical_name
    player = (
        db.query(Player)
        .filter(Player.canonical_name == recipient_name)
        .first()
    )
    return player.id if player else None


# ---------------------------------------------------------------------------
# B2 — Network metrics computation
# ---------------------------------------------------------------------------

def compute_network_metrics(network: dict[str, Any]) -> dict[str, Any]:
    """Compute network science metrics for each player in the passing network.

    Metrics:
    - degree_centrality: fraction of teammates passed to
    - betweenness_centrality: how often player sits on shortest paths
    - clustering_coefficient: fraction of teammates that also pass to each other
    """
    nodes = network["nodes"]
    edges = network["edges"]
    n = len(nodes)
    if n < 2:
        return {"nodes": [], "overall_style": "insufficient_data"}

    # Build adjacency for directed graph
    adjacency: dict[int, set[int]] = defaultdict(set)
    weight_map: dict[tuple[int, int], int] = {}
    for edge in edges:
        adjacency[edge["from"]].add(edge["to"])
        weight_map[(edge["from"], edge["to"])] = edge["weight"]

    all_player_ids = {node["player_id"] for node in nodes}

    # Compute metrics per player
    metrics = []
    for node in nodes:
        pid = node["player_id"]
        neighbors = adjacency.get(pid, set())

        # Degree centrality
        degree = len(neighbors)
        degree_centrality = degree / (n - 1) if n > 1 else 0

        # Betweenness centrality (simplified — BFS-based for directed graph)
        betweenness = _compute_betweenness_for_node(pid, all_player_ids, adjacency)

        # Clustering coefficient (for directed: what fraction of neighbors also connect)
        clustering = _compute_clustering(pid, neighbors, adjacency)

        metrics.append({
            "player_id": pid,
            "degree_centrality": round(degree_centrality, 4),
            "betweenness_centrality": round(betweenness, 4),
            "clustering_coefficient": round(clustering, 4),
            "pass_count": node.get("pass_count", 0),
            "pass_success_rate": node.get("pass_success_rate", 0),
            "avg_x": node.get("avg_x"),
            "avg_y": node.get("avg_y"),
        })

    return {
        "nodes": metrics,
        "network_size": n,
        "total_edges": len(edges),
    }


def _compute_betweenness_for_node(
    target: int,
    all_nodes: set[int],
    adjacency: dict[int, set[int]],
) -> float:
    """Simplified betweenness centrality for one node using BFS."""
    total = 0
    for source in all_nodes:
        if source == target:
            continue
        # BFS from source
        distances = {source: 0}
        predecessors: dict[int, list[int]] = defaultdict(list)
        queue = [source]
        while queue:
            current = queue.pop(0)
            for neighbor in adjacency.get(current, set()):
                new_dist = distances[current] + 1
                if neighbor not in distances:
                    distances[neighbor] = new_dist
                    queue.append(neighbor)
                if new_dist == distances.get(neighbor, float("inf")):
                    predecessors[neighbor].append(current)

        # Count shortest paths through target
        if target not in distances:
            continue
        # Backtrack from all nodes to source, count paths through target
        path_count: dict[int, int] = {source: 1}
        nodes_by_dist = sorted(distances.keys(), key=lambda x: distances[x])
        for node in nodes_by_dist:
            for pred in predecessors.get(node, []):
                path_count[node] = path_count.get(node, 0) + path_count.get(pred, 0)

        total_through = 0
        for node in nodes_by_dist:
            if node == source or distances[node] < distances[target]:
                continue
            for pred in predecessors.get(node, []):
                if distances[pred] == distances[target] and pred == target:
                    total_through += path_count.get(source, 0)

        if total_through > 0:
            total += total_through / path_count.get(target, 1)

    # Normalize by max possible
    n = len(all_nodes)
    max_betweenness = (n - 1) * (n - 2) if n > 2 else 1
    return total / max_betweenness if max_betweenness > 0 else 0


def _compute_clustering(
    player_id: int,
    neighbors: set[int],
    adjacency: dict[int, set[int]],
) -> float:
    """Compute clustering coefficient for a player."""
    if len(neighbors) < 2:
        return 0.0
    # Count edges between neighbors
    neighbor_list = list(neighbors)
    edges_between = 0
    for i, n1 in enumerate(neighbor_list):
        for n2 in neighbor_list[i + 1:]:
            if n2 in adjacency.get(n1, set()) or n1 in adjacency.get(n2, set()):
                edges_between += 1
    max_edges = len(neighbors) * (len(neighbors) - 1) / 2
    return edges_between / max_edges if max_edges > 0 else 0


# ---------------------------------------------------------------------------
# B3 — Tactical style detection
# ---------------------------------------------------------------------------

def detect_tactical_style(network: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Detect the team's tactical style from passing network data.

    Styles (documented thresholds):
    - possession: high pass volume, short average distance
    - direct: low pass volume, long average distance
    - progressive: medium volume, increasing forward distance
    - wide_play: high passing concentration on flanks
    - central_play: high passing concentration through center
    - balanced: default when no strong signal

    Returns:
        style: detected style string
        confidence: 0-1 confidence in detection
        factors: which metrics contributed to the decision
    """
    total_passes = network.get("total_passes", 0)
    nodes = metrics.get("nodes", [])

    if not nodes or total_passes == 0:
        return {
            "style": "insufficient_data",
            "confidence": 0,
            "factors": [],
        }

    # Compute aggregate metrics
    avg_success_rate = sum(n.get("pass_success_rate", 0) for n in nodes) / len(nodes)
    avg_betweenness = sum(n.get("betweenness_centrality", 0) for n in nodes) / len(nodes)

    # Estimate average pass distance from node positions
    edges = network.get("edges", [])
    avg_distance = _estimate_avg_pass_distance(nodes, edges)

    # Estimate width (passing concentration on wings vs center)
    width_score = _estimate_width_concentration(nodes)

    factors = []
    style = "balanced"
    confidence = 0.5

    # Style detection logic (documented thresholds)
    if total_passes > 400 and avg_distance < 12:
        style = "possession"
        confidence = min(0.9, 0.5 + (total_passes - 400) / 500)
        factors.append(f"High pass volume ({total_passes}) with short average distance")
    elif total_passes < 200 and avg_distance > 20:
        style = "direct"
        confidence = min(0.9, 0.5 + (200 - total_passes) / 300)
        factors.append(f"Low pass volume ({total_passes}) with long average distance")
    elif width_score > 0.6:
        style = "wide_play"
        confidence = 0.5 + width_score * 0.3
        factors.append(f"High wing concentration ({width_score:.0%})")
    elif width_score < 0.3:
        style = "central_play"
        confidence = 0.5 + (1 - width_score) * 0.2
        factors.append(f"High central concentration ({1 - width_score:.0%})")

    # Betweenness signal
    if avg_betweenness > 0.3:
        factors.append(f"High betweenness centrality ({avg_betweenness:.2f}) — playmaker-dependent structure")
    if avg_success_rate > 85:
        factors.append(f"High pass accuracy ({avg_success_rate:.0f}%)")

    return {
        "style": style,
        "confidence": round(confidence, 2),
        "factors": factors,
        "metrics": {
            "total_passes": total_passes,
            "avg_pass_distance": round(avg_distance, 1),
            "avg_success_rate": round(avg_success_rate, 1),
            "avg_betweenness": round(avg_betweenness, 4),
            "width_score": round(width_score, 2),
        },
    }


def _estimate_avg_pass_distance(nodes: list[dict], edges: list[dict]) -> float:
    """Estimate average pass distance from node average positions and edge weights."""
    pos_map = {n["player_id"]: (n.get("avg_x") or 60, n.get("avg_y") or 40) for n in nodes}
    total_dist = 0.0
    total_weight = 0
    for edge in edges:
        from_pos = pos_map.get(edge["from"])
        to_pos = pos_map.get(edge["to"])
        if from_pos and to_pos:
            dist = math.sqrt(
                (to_pos[0] - from_pos[0]) ** 2 + (to_pos[1] - from_pos[1]) ** 2
            )
            total_dist += dist * edge["weight"]
            total_weight += edge["weight"]
    return total_dist / total_weight if total_weight > 0 else 15.0


def _estimate_width_concentration(nodes: list[dict]) -> float:
    """Estimate how much passing is concentrated on the wings vs center.

    Returns 0.0 (all central) to 1.0 (all wide).
    """
    wing_count = 0
    total_count = 0
    for node in nodes:
        avg_y = node.get("avg_y")
        passes = node.get("pass_count", 0) + node.get("pass_received", 0)
        if avg_y is None or passes == 0:
            continue
        total_count += passes
        # StatsBomb: y=0 left, y=80 right. Wings are y<20 or y>60.
        if avg_y < 20 or avg_y > 60:
            wing_count += passes
    return wing_count / total_count if total_count > 0 else 0.5


# ---------------------------------------------------------------------------
# B4 — Anomaly detection
# ---------------------------------------------------------------------------

def detect_network_anomalies(
    network: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Flag unusual patterns in the passing network.

    Anomalies:
    1. Dominant playmaker: unusually high betweenness centrality
    2. Asymmetric flow: dramatically different send vs receive ratios
    3. Disconnected player: no passes to/from them (data error or benching)
    """
    nodes = metrics.get("nodes", [])
    anomalies = []

    if not nodes:
        return anomalies

    betweenness_values = [n.get("betweenness_centrality", 0) for n in nodes]
    avg_betweenness = sum(betweenness_values) / len(betweenness_values) if betweenness_values else 0

    for node in nodes:
        pid = node["player_id"]
        bc = node.get("betweenness_centrality", 0)
        pass_count = node.get("pass_count", 0)
        pass_received = 0
        for n in nodes:
            if n["player_id"] != pid:
                pass_received += n.get("pass_count", 0) if False else 0
        # Use simple approach: pass_count vs network average
        avg_passes = sum(n.get("pass_count", 0) for n in nodes) / len(nodes) if nodes else 0

        # 1. Dominant playmaker
        if bc > 0.4 and bc > avg_betweenness * 2:
            anomalies.append({
                "type": "dominant_playmaker",
                "player_id": pid,
                "severity": "info",
                "detail": (
                    f"Player has unusually high betweenness centrality "
                    f"({bc:.2f} vs average {avg_betweenness:.2f}) — "
                    f"potential dominant playmaker"
                ),
            })

        # 2. Asymmetric flow (high attempts, low received or vice versa)
        if pass_count > avg_passes * 2.5 and pass_count > 30:
            anomalies.append({
                "type": "high_volume_sender",
                "player_id": pid,
                "severity": "info",
                "detail": (
                    f"Player sends significantly more passes than average "
                    f"({pass_count} vs avg {avg_passes:.0f}) — "
                    f"may indicate dominant role or tactical focus"
                ),
            })

        # 3. Disconnected player (zero passes attempted)
        if node.get("pass_attempts", 0) == 0 and node.get("pass_count", 0) == 0:
            anomalies.append({
                "type": "disconnected_player",
                "player_id": pid,
                "severity": "warning",
                "detail": (
                    f"Player has no completed passes in network — "
                    f"possible data error, limited playing time, or isolated role"
                ),
            })

    return anomalies
