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

Phase 6 (similarity-explanation-method.md): every result also carries a
structured `explanation` — "matched strengths" (metrics where both players rank
highly and that contributed most to the cosine score) and "key differences"
(metrics with the largest percentile-point gaps, with the stronger player
stated). The decomposition reuses the dot product, norms, and shared-metric
set already computed for ranking, so the explanation is arithmetic on the same
intermediates as the score and cannot diverge from it.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import PercentileSnapshot, Player, StatSnapshot, Team

MIN_SHARED_METRICS = 5

# Phase 6 explanation thresholds (documented in
# docs/analytics/similarity-explanation-method.md §3). Boundary values are
# inclusive; the two rules are mutually exclusive by construction (matched
# requires gap <= 20, key requires gap >= 25).
MATCHED_STRENGTH_MIN_PERCENTILE = 70.0
MATCHED_STRENGTH_MAX_DIFF = 20.0
KEY_DIFFERENCE_MIN_GAP = 25.0
MAX_EXPLAINED_ITEMS = 3

EXCLUDED_REASON = (
    "no published percentile for one or both players (a missing value is "
    "N/A, never a zero)"
)


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


def _cosine_with_components(
    a: dict[str, float], b: dict[str, float], min_shared_metrics: int
) -> tuple[float, int, dict[str, float]]:
    """Cosine over the shared metric subset + per-metric contributions.

    Returns (similarity, shared count, contributions) where each contribution
    is c_i = a_i·b_i / (‖a‖·‖b‖) over the shared subset — the metric's share of
    the headline score (Σ c_i = similarity). Reuses the same dot product and
    norms for both, so the Phase 6 explanation is guaranteed-consistent with
    the score it explains.

    `min_shared_metrics` is passed explicitly (never read from module state) so
    behaviour cannot depend on the call order of previous invocations.
    """
    shared = [m for m in a if m in b]
    if len(shared) < min_shared_metrics:
        return 0.0, len(shared), {}
    dot = sum(a[m] * b[m] for m in shared)
    norm_a = math.sqrt(sum(a[m] * a[m] for m in shared))
    norm_b = math.sqrt(sum(b[m] * b[m] for m in shared))
    if norm_a == 0 or norm_b == 0:
        return 0.0, len(shared), {}
    denominator = norm_a * norm_b
    contributions = {m: round(a[m] * b[m] / denominator, 6) for m in shared}
    return round(dot / denominator, 4), len(shared), contributions


def _cosine_similarity(
    a: dict[str, float], b: dict[str, float], min_shared_metrics: int
) -> tuple[float, int]:
    """Cosine over the shared metric subset. Returns (similarity, shared count)."""
    sim, shared, _ = _cosine_with_components(a, b, min_shared_metrics)
    return sim, shared


def _explain_from_components(
    anchor: dict[str, float],
    candidate: dict[str, float],
    contributions: dict[str, float],
    *,
    group: str,
    registry: dict[str, Any],
    shared_count: int,
) -> dict[str, Any]:
    """Build the structured explanation from already-computed intermediates.

    This is the Phase 6 B2 reuse path: `get_similar_players` computes
    (similarity, shared, contributions) once per candidate and hands the
    intermediates here — no second computation, no re-query.
    """
    metric_ids = (
        registry["gk_metrics"] if group == "GK" else registry["outfield_metrics"]
    )
    names = registry["metrics"]
    shared = [m for m in metric_ids if m in anchor and m in candidate]

    matched: list[dict[str, Any]] = []
    for m in shared:
        if (
            anchor[m] >= MATCHED_STRENGTH_MIN_PERCENTILE
            and candidate[m] >= MATCHED_STRENGTH_MIN_PERCENTILE
            and abs(anchor[m] - candidate[m]) <= MATCHED_STRENGTH_MAX_DIFF
        ):
            matched.append(
                {
                    "metric": m,
                    "metric_name": names[m]["name"],
                    "player_a_percentile": anchor[m],
                    "player_b_percentile": candidate[m],
                    "difference": round(abs(anchor[m] - candidate[m]), 2),
                    "contribution": contributions.get(m, 0.0),
                }
            )
    matched.sort(key=lambda item: (-item["contribution"], item["metric"]))
    matched = matched[:MAX_EXPLAINED_ITEMS]

    key_differences: list[dict[str, Any]] = []
    for m in shared:
        gap = anchor[m] - candidate[m]
        if abs(gap) >= KEY_DIFFERENCE_MIN_GAP:
            key_differences.append(
                {
                    "metric": m,
                    "metric_name": names[m]["name"],
                    "player_a_percentile": anchor[m],
                    "player_b_percentile": candidate[m],
                    "difference": round(abs(gap), 2),
                    "stronger_player": "player_a" if gap > 0 else "player_b",
                }
            )
    key_differences.sort(key=lambda item: (-item["difference"], item["metric"]))
    key_differences = key_differences[:MAX_EXPLAINED_ITEMS]

    return {
        "matched_strengths": matched,
        "key_differences": key_differences,
        # Carries the registry display name so the UI can name excluded
        # metrics in human terms (D1 naming consistency, same source as the
        # Radar tool) without a second lookup.
        "excluded_metrics": [
            {"metric": m, "metric_name": names[m]["name"]}
            for m in metric_ids
            if m not in shared
        ],
        "excluded_reason": EXCLUDED_REASON,
        "shared_metrics": shared_count,
    }


def build_similarity_explanation(
    anchor: dict[str, float],
    candidate: dict[str, float],
    *,
    group: str,
    registry: dict[str, Any],
    min_shared_metrics: int = MIN_SHARED_METRICS,
) -> dict[str, Any] -> None:
    """Pure explanation builder (unit-testable without a database).

    Every number is a real value from the two percentile vectors; metric names
    come from the Metric Registry (the same source the Radar tool reads).
    """
    _, shared_count, contributions = _cosine_with_components(
        anchor, candidate, min_shared_metrics
    )
    return _explain_from_components(
        anchor,
        candidate,
        contributions,
        group=group,
        registry=registry,
        shared_count=shared_count,
    )


def get_similar_players(
    db: Session,
    player_id: int,
    *,
    limit: int = 5,
    min_shared_metrics: int = MIN_SHARED_METRICS,
) -> list[dict[str, Any]] -> None:
    """Nearest neighbours for a player, same position group and league tier.

    Returns [] when the player has no published percentile vector (unqualified
    or blocked) — callers render the explicit empty state, never a fake list.

    Each result now carries an `explanation` object (Phase 6): matched
    strengths / key differences / excluded metrics derived from the same
    cosine intermediates used to rank the candidate.
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

    registry = load_registry()
    cohort = _latest_rows_per_player(db, position_group=group, league_tier=tier)

    scored: list[tuple[float, int, int]] = []
    components: dict[int, dict[str, float]] = {}
    for pid, (vector, index) in cohort.items():
        if pid == player_id:
            continue
        sim, shared, contributions = _cosine_with_components(
            anchor_vector, vector, min_shared_metrics
        )
        if shared < min_shared_metrics or sim <= 0.0:
            continue
        scored.append((sim, pid, shared))
        components[pid] = contributions

    scored.sort(key=lambda item: (-item[0], item[1]))
    top = scored[:limit]
    if not top:
        return []

    from app.models import League
    from app.queries.player_queries import player_slug_map

    players = {
        p.id: p
        for p in db.query(Player)
        .filter(Player.id.in_([pid for _, pid, _ in top]))
        .all()
    }
    # Batch-load only the teams/leagues referenced by these players
    team_ids = {p.current_team_id for p in players.values() if p.current_team_id}
    teams = {
        t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()
    } if team_ids else {}
    league_ids = {t.league_id for t in teams.values() if t.league_id}
    leagues = {
        lg.id: lg for lg in db.query(League).filter(League.id.in_(league_ids)).all()
    } if league_ids else {}
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
                "explanation": _explain_from_components(
                    anchor_vector,
                    vector,
                    components[pid],
                    group=group,
                    registry=registry,
                    shared_count=shared,
                ),
            }
        )
    return results
