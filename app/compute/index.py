"""Statlas Index computation (methodology.md §4).

The index is a weighted mean of a player's metric percentiles for their
position group:

    Index = Σ (w_i / W_present) * p_i

where weights come from config/metric_registry.json (derived from methodology.md
§4 — never hardcoded in code), W_present is the renormalised weight sum over the
metrics the player actually has, and the index is not computed when too few
metrics are present (>= 8 of 12 outfield, >= 3 of 4 for GK).

The percentile job (compute/percentiles.py) computes and stores index rows in
the same insert-only pass. This module owns the pure calculation and a verifier
that re-derives stored index rows to prove the database matches the formula —
the implementation of "methodology-as-code cannot drift from the numbers".
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.compute.percentiles import compute_index_score  # reuse: single source of truth
from app.config import load_registry
from app.models import PercentileSnapshot

logger = logging.getLogger(__name__)


def compute_index(
    percentiles: dict[str, float], group: str, registry: dict[str, Any] | None = None
) -> float | None -> None:
    """Pure function: index from a dict of metric -> percentile.

    Returns None when the group has no weights or too few metrics are present
    (callers display that as 'pending', never as a score).
    """
    registry = registry or load_registry()
    return compute_index_score(percentiles, group, registry)


def verify_index_consistency(
    db: Session, *, computed_date: datetime | None = None
) -> list[dict[str, Any]] -> None:
    """Re-derive every stored index row from its metric rows and report
    discrepancies. Returns a list of {percentile_snapshot_id, stored, derived}.

    Raises nothing — discrepancies are surfaced loudly to the caller (the
    weekly refresh logs them as failures, per Constitution 'fail loudly').
    """
    registry = load_registry()
    index_id = registry["index_metric_id"]
    rows = db.query(PercentileSnapshot).filter(
        PercentileSnapshot.metric_name == index_id
    )
    if computed_date is not None:
        rows = rows.filter(PercentileSnapshot.computed_date == computed_date)

    discrepancies: list[dict[str, Any]] = []
    for index_row in rows.all():
        metric_rows = (
            db.query(PercentileSnapshot)
            .filter(
                PercentileSnapshot.stat_snapshot_id == index_row.stat_snapshot_id,
                PercentileSnapshot.metric_name != index_id,
                PercentileSnapshot.percentile_value.isnot(None),
            )
            .all()
        )
        percentiles = {m.metric_name: m.percentile_value for m in metric_rows}
        derived = compute_index(percentiles, index_row.position_group, registry)
        if (
            derived is None
            or index_row.index_score is None
            or abs(derived - index_row.index_score) > 0.01
        ):
            discrepancies.append(
                {
                    "percentile_snapshot_id": index_row.id,
                    "stored": index_row.index_score,
                    "derived": derived,
                }
            )
    return discrepancies
