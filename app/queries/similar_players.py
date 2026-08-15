"""Similar players — real nearest-neighbour computation (Phase 2 B4).

Similarity is cosine similarity across the *published percentile vector*
within the same {position group, league tier} cohort, computed on the metrics
present for BOTH players. This is checkable, not a black box: the UI states the
basis ("similar based on their percentile profiles for progression and
defensive metrics"), and the shared-metric count is returned with each result.

    similarity = Σ p_i·q_i / (‖p‖·‖q‖)   over the shared metric subset

Metrics absent for either player are excluded from that pair's similarity (a
missing percentile is N/A, never a zero — Constitution §3 null-vs-zero rule).
A pair with fewer than `min_shared_metrics` in common is not considered.
"""
from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import PercentileSnapshot, Player, StatSnapshot, Team

MIN_SHARED_METRICS = 5


def _latest_rows_per_player(
    db: Session, *, position_group: str, league_tier: str
) -> dict[int, tuple[dict[str, float], float | None]]:
    """Latest published percentile vector + index per player in a cohort.

    Matches the leaderboard's "latest snapshot per player" rule so similarity
    is computed against the same values a user sees on leaderboards.
    """
    rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.position_group == position_group,
            PercentileSnapshot.league_tier == league_tier,
        )
        .all()
    )
    best: dict[int, tuple[StatSnapshot, dict[str, float], float | None]] = {}
    index_id = load_registry()["index_metric_id"]
    for percentile, snap in rows:
        existing = best.get(snap.player_id)
        if existing is not None and snap.scrape_date < existing[0].scrape_date:
            continue
        vector, index = best.get(snap.player_id, (None, {}, None))[1:]
        if percentile.metric_name == index_id:
            index = percentile.index_score
        elif percentile.percentile_value is not None:
            vector[percentile.metric_name] = percentile.percentile_value
        best[snap.player_id] = (snap, vector, index)
    return {pid: (vector, index) for pid, (_, vector, index) in best.items()}


def _cosine_similarity(a: dict[str, float], b: dict[str, float], min_shared_metrics: int) -> tuple[float, int]:
    """Cosine over the shared metric subset. Returns (similarity, shared count).

    `min_shared_metrics` is passed explicitly (never read from module state) so
    behaviour cannot depend on the call order of previous invocations.
    """
    shared = [m for m in a if m in b]
    if len(shared) < min_shared_metrics:
        return 0.0, len(shared)
    dot = sum(a[m] * b[m] for m in shared)
    norm_a = math.sqrt(sum(a[m] * a[m] for m in shared))
    norm_b = math.sqrt(sum(b[m] * b[m] for m in shared))
    if norm_a == 0 or norm_b == 0:
        return 0.0, len(shared)
    return round(dot / (norm_a * norm_b), 4), len(shared)


def get_similar_players(
    db: Session,
    player_id: int,
    *,
    limit: int = 5,
    min_shared_metrics: int = MIN_SHARED_METRICS,
) -> list[dict[str, Any]]:
    """Nearest neighbours for a player, same position group and league tier.

    Returns [] when the player has no published percentile vector (unqualified
    or blocked) — callers render the explicit empty state, never a fake list.
    """
    anchor_rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            StatSnapshot.player_id == player_id,
        )
        .order_by(StatSnapshot.scrape_date.desc(), PercentileSnapshot.id.desc())
        .first()
    )
    if anchor_rows is None:
        return []
    _anchor_pct, _ = anchor_rows
    group = _anchor_pct.position_group
    tier = _anchor_pct.league_tier

    anchor_vector, anchor_index = _latest_rows_per_player(
        db, position_group=group, league_tier=tier
    ).get(player_id, ({}, None))
    if not anchor_vector:
        return []

    cohort = _latest_rows_per_player(db, position_group=group, league_tier=tier)

    scored: list[tuple[float, int, int]] = []
    for pid, (vector, index) in cohort.items():
        if pid == player_id:
            continue
        sim, shared = _cosine_similarity(anchor_vector, vector, min_shared_metrics)
        if shared < min_shared_metrics or sim <= 0.0:
            continue
        scored.append((sim, pid, shared))

    scored.sort(key=lambda item: (-item[0], item[1]))
    top = scored[:limit]
    if not top:
        return []

    from app.models import League
    from app.queries.player_queries import player_slug_map

    players = {p.id: p for p in db.query(Player).filter(Player.id.in_([pid for _, pid, _ in top])).all()}
    teams = {t.id: t for t in db.query(Team).all()}
    leagues = {league.id: league for league in db.query(League).all()}
    slugs = {p["player_id"]: p["slug"] for p in player_slug_map(db)}

    results: list[dict[str, Any]] = []
    for sim, pid, shared in top:
        player = players[pid]
        team = teams.get(player.current_team_id)
        league = leagues.get(team.league_id) if team else None
        vector, index = cohort[pid]
        results.append(
            {
                "player_id": pid,
                "name": player.canonical_name,
                "slug": slugs.get(pid),
                "position_group": player.position_group,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "similarity": sim,
                "shared_metrics": shared,
                "index": index,
                "anchor_index": anchor_index,
            }
        )
    return results

