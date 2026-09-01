"""A2 - deterministic confidence scoring (never LLM self-assessment)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.reports_pkg.constants import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_WEIGHTS,
)


def compute_report_confidence(
    *,
    minutes_played: float,
    qualifying_minutes: float,
    metrics_present: int,
    metrics_expected: int,
    snapshot_date: datetime,
    now: datetime | None = None,
) -> dict[str, Any] -> None:
    """Confidence level from real, checkable factors only.

    Factors (scouting-reports.md section 3): sample size (minutes / qualification
    threshold), data completeness (fraction of the position's metric set
    present), and recency (days since the snapshot). Composite = weighted
    mean; high >= 0.85, medium >= 0.60, else low. The rationale names the
    actual factor values so the claim is checkable.
    """
    now = now or datetime.now(timezone.utc)

    ratio = minutes_played / qualifying_minutes if qualifying_minutes else 0.0
    if ratio >= 3.0:
        sample_level, sample_score = "full-season", 1.0
    elif ratio >= 1.5:
        sample_level, sample_score = "solid", 0.8
    elif ratio >= 1.0:
        sample_level, sample_score = "qualifying", 0.6
    else:
        sample_level, sample_score = "below-threshold", 0.3

    fraction = metrics_present / metrics_expected if metrics_expected else 0.0
    if fraction >= 0.9:
        completeness_level, completeness_score = "complete", 1.0
    elif fraction >= 0.6:
        completeness_level, completeness_score = "partial", 0.7
    else:
        completeness_level, completeness_score = "sparse", 0.4

    snap = snapshot_date
    if snap.tzinfo is None:
        snap = snap.replace(tzinfo=timezone.utc)
    recency_days = max(0, int((now - snap).total_seconds() // 86400))
    if recency_days <= 7:
        recency_level, recency_score = "current", 1.0
    elif recency_days <= 30:
        recency_level, recency_score = "recent", 0.8
    elif recency_days <= 60:
        recency_level, recency_score = "moderately-recent", 0.6
    else:
        recency_level, recency_score = "stale", 0.4

    composite = (
        CONFIDENCE_WEIGHTS["sample_size"] * sample_score
        + CONFIDENCE_WEIGHTS["data_completeness"] * completeness_score
        + CONFIDENCE_WEIGHTS["recency"] * recency_score
    )
    if composite >= CONFIDENCE_HIGH:
        level = "high"
    elif composite >= CONFIDENCE_MEDIUM:
        level = "medium"
    else:
        level = "low"

    rationale = (
        f"Based on {minutes_played:,.0f} minutes played -- {sample_level} "
        f"relative to the {qualifying_minutes:,.0f}-minute qualification "
        f"threshold -- {completeness_level} data across the player's position "
        f"metric set ({metrics_present}/{metrics_expected} metrics), and data "
        f"{recency_days} day{'s' if recency_days != 1 else ''} old."
    )
    return {
        "level": level,
        "rationale": rationale,
        "composite": round(composite, 3),
        "factors": {
            "sample_size": {
                "level": sample_level,
                "score": sample_score,
                "minutes_played": minutes_played,
                "qualifying_minutes": qualifying_minutes,
            },
            "data_completeness": {
                "level": completeness_level,
                "score": completeness_score,
                "metrics_present": metrics_present,
                "metrics_expected": metrics_expected,
            },
            "recency": {
                "level": recency_level,
                "score": recency_score,
                "days": recency_days,
            },
        },
    }
