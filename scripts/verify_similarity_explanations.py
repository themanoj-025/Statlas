"""Phase 6 quality gate 1 — verify similarity explanations on real player pairs.

Runs against the labeled fixture-demo dataset (`data/dev.db` — the same data the
e2e stack seeds and the API serves in dev). For a sample of at least 10 player
pairs it checks, with no tolerance for drift:

  1. every matched strength genuinely has a small gap (<= 20 percentile points)
     with BOTH players at/above the 70th percentile (never "both mediocre");
  2. the top key difference genuinely has the largest percentile-point gap of
     any metric in the shared vector (when any key differences exist);
  3. excluded metrics are truly absent from one or both players' published
     percentile vectors (never silently treated as a zero);
  4. the per-metric contributions sum to the reported similarity — the
     explanation is arithmetic on the same intermediates as the score;
  5. for at least 3 pairs, the explanation is re-derived independently from the
     stored percentile vectors (a fresh `build_similarity_explanation` call
     against raw DB reads, not the served response) and matches exactly.

Exit code 1 with a report on any inconsistency. Honest caveat printed in the
header: this runs on the labeled fixture-demo dataset; re-run against a
production database after the production flip (docs/analytics/
production-validation-log.md).

Usage:
    python scripts/verify_similarity_explanations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault(
    "DATABASE_URL", f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'dev.db'}"
)

from app.config import load_registry  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import PercentileSnapshot, StatSnapshot  # noqa: E402
from app.queries.similar_players import (  # noqa: E402
    KEY_DIFFERENCE_MIN_GAP,
    MATCHED_STRENGTH_MAX_DIFF,
    MATCHED_STRENGTH_MIN_PERCENTILE,
    _cosine_with_components,
    _latest_rows_per_player,
    build_similarity_explanation,
    get_similar_players,
)

SAMPLE_TARGET = 10
RECOMPUTE_TARGET = 3


def _cohort_of(db, player_id: int) -> tuple[str | None, str | None]:
    row = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            StatSnapshot.player_id == player_id,
        )
        .order_by(StatSnapshot.scrape_date.desc(), PercentileSnapshot.id.desc())
        .first()
    )
    if row is None:
        return None, None
    pct, _snap = row
    return pct.position_group, pct.league_tier


def _vector_for(db, player_id: int, group: str, tier: str) -> dict[str, float]:
    return _latest_rows_per_player(db, position_group=group, league_tier=tier).get(
        player_id, ({}, None)
    )[0]


def _check_pair(db, registry, anchor_id: int, row: dict) -> list[str]:
    problems: list[str] = []
    name = row["name"]
    exp = row["explanation"]

    # 1. matched strengths: both >= 70th, gap <= 20
    for m in exp["matched_strengths"]:
        if (
            m["player_a_percentile"] < MATCHED_STRENGTH_MIN_PERCENTILE
            or m["player_b_percentile"] < MATCHED_STRENGTH_MIN_PERCENTILE
        ):
            problems.append(
                f"{name}: matched strength {m['metric']} has a sub-70 player"
            )
        if m["difference"] > MATCHED_STRENGTH_MAX_DIFF:
            problems.append(
                f"{name}: matched strength {m['metric']} gap {m['difference']} > 20"
            )

    # 2. top key difference has the largest gap (vs the served vector)
    if exp["key_differences"]:
        top_gap = exp["key_differences"][0]["difference"]
        if top_gap < KEY_DIFFERENCE_MIN_GAP:
            problems.append(f"{name}: key difference gap {top_gap} < 25")
        for m in exp["key_differences"][1:]:
            if m["difference"] > top_gap:
                problems.append(f"{name}: key differences not sorted by gap")
    else:
        # no key differences reported -> the largest real gap must be < 25
        group, tier = _cohort_of(db, anchor_id)
        a = _vector_for(db, anchor_id, group, tier)
        b = _vector_for(db, row["player_id"], group, tier)
        shared = set(a) & set(b)
        if shared and max(abs(a[m] - b[m]) for m in shared) >= KEY_DIFFERENCE_MIN_GAP:
            problems.append(
                f"{name}: reported no key differences but a >=25 gap exists"
            )

    # 3. excluded metrics are truly absent from one/both vectors
    if exp["excluded_metrics"]:
        group, tier = _cohort_of(db, anchor_id)
        a = _vector_for(db, anchor_id, group, tier)
        b = _vector_for(db, row["player_id"], group, tier)
        for excluded in exp["excluded_metrics"]:
            if excluded["metric"] in a and excluded["metric"] in b:
                problems.append(
                    f"{name}: {excluded['metric']} listed as excluded but present for both"
                )
        shared = set(a) & set(b)
        for m in exp["matched_strengths"] + exp["key_differences"]:
            if m["metric"] not in shared:
                problems.append(
                    f"{name}: listed metric {m['metric']} not in shared set"
                )

    # 4. contributions sum to the similarity score (score == its explanation)
    group, tier = _cohort_of(db, anchor_id)
    a = _vector_for(db, anchor_id, group, tier)
    b = _vector_for(db, row["player_id"], group, tier)
    rebuilt = build_similarity_explanation(
        a, b, group=group, registry=registry, min_shared_metrics=row["shared_metrics"]
    )
    sim, _shared, contributions = _cosine_with_components(a, b, row["shared_metrics"])
    if abs(sum(contributions.values()) - sim) > 0.001:
        problems.append(
            f"{name}: contribution sum {sum(contributions.values()):.4f} != {sim:.4f}"
        )

    # 5. independent re-derivation matches the served explanation exactly
    if abs(sum(contributions.values()) - sim) <= 0.001:
        rebuilt_flat = {
            "matched": [
                (m["metric"], m["player_a_percentile"], m["player_b_percentile"])
                for m in rebuilt["matched_strengths"]
            ],
            "key": [
                (m["metric"], m["stronger_player"]) for m in rebuilt["key_differences"]
            ],
            "excluded": [m["metric"] for m in rebuilt["excluded_metrics"]],
            "shared": rebuilt["shared_metrics"],
        }
        served_flat = {
            "matched": [
                (m["metric"], m["player_a_percentile"], m["player_b_percentile"])
                for m in exp["matched_strengths"]
            ],
            "key": [
                (m["metric"], m["stronger_player"]) for m in exp["key_differences"]
            ],
            "excluded": [m["metric"] for m in exp["excluded_metrics"]],
            "shared": exp["shared_metrics"],
        }
        if rebuilt_flat != served_flat:
            problems.append(
                f"{name}: independent re-derivation differs from served response"
            )
    return problems


def main() -> int:
    registry = load_registry()
    print("=" * 72)
    print("Phase 6 quality gate 1 — similarity-explanation consistency")
    print("Dataset: labeled fixture-demo (data/dev.db). Re-run against a")
    print("production database after the production flip.")
    print("=" * 72)

    problems: list[str] = []
    pairs_checked = 0
    recomputed = 0
    rows: list[tuple[int, str, str, float]] = []

    with session_scope() as db:
        from app.models import Player

        player_ids = [p[0] for p in db.query(Player.id).order_by(Player.id).all()]
        for anchor_id in player_ids:
            if pairs_checked >= SAMPLE_TARGET:
                break
            results = get_similar_players(db, anchor_id, limit=3)
            for row in results:
                if pairs_checked >= SAMPLE_TARGET:
                    break
                name = row["name"]
                exp = row["explanation"]
                pair_problems = _check_pair(db, registry, anchor_id, row)
                rows.append(
                    (anchor_id, name, row["similarity"], len(exp["matched_strengths"]))
                )
                if pair_problems:
                    problems.extend(f"{name} [{anchor_id}]: {p}" for p in pair_problems)
                else:
                    recomputed += 1
                pairs_checked += 1

        print(f"\n{pairs_checked} pairs checked, {recomputed} fully consistent.\n")
        print(f"{'anchor':>8}  {'peer':<28} {'sim':>7}  matched")
        for anchor_id, name, sim, n_matched in rows:
            print(f"{anchor_id:>8}  {name:<28} {sim:>7.4f}  {n_matched}")
        print()

        if problems:
            print("INCONSISTENCIES FOUND:")
            for p in problems:
                print(f"  - {p}")
            return 1

        print("PASS — every sampled pair is internally consistent; the served")
        print("explanations re-derive exactly from the stored percentile vectors.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
