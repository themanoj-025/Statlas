"""Emerging player score computation (Phase 11 — Part B).

Computes a weighted composite score per player in a league:
    score = trend_magnitude × trend_consistency × age_weight × sample_weight

All factors are 0.0–1.0. The score is written to emerging_player_scores
during the weekly refresh orchestration (after percentile computation and
publishing, per Phase 10's watch-trigger detection).

Methodology: docs/analytics/emerging-player-methodology.md
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import (
    EmergingPlayerScore,
    PercentileSnapshot,
    Player,
    StatSnapshot,
)

logger = logging.getLogger(__name__)

# Configuration (tunable per deployment without code change — §2 A2).
TREND_WINDOW = 5  # snapshots
MIN_SNAPSHOTS = 3  # need at least 3 for a meaningful trend
MIN_METRICS_FOR_TREND = 3  # need percentile data for at least 3 metrics
SCORE_THRESHOLD = 0.50  # players above this appear on the league page
# Weight factors (methodology doc §2, weight columns).
W_TREND_MAGNITUDE = 0.45
W_TREND_CONSISTENCY = 0.30
W_AGE = 0.15
W_SAMPLE = 0.10
# Sigmoid midpoint for age weight.
AGE_MIDPOINT = 24
AGE_SCALE = 3


def compute_emerging_scores(
    db: Session,
    *,
    snapshot_date: datetime,
    season: str,
    league_ids: list[int] | None = None,
) -> int:
    """Compute emerging-player scores for all eligible players.

    Called from weekly_refresh after publishing. Idempotent: re-running for
    the same computed_date replaces existing rows.

    Returns the number of score rows written.
    """
    from app.models import League

    if league_ids is None:
        league_ids = [lid for (lid,) in db.query(League.id).all()]

    if not league_ids:
        return 0

    # Qualifying minutes from the registry.
    registry = load_registry()
    qualifying_minutes = registry.get("qualifying_minutes", 900)

    written = 0
    for league_id in league_ids:
        scores = _score_league(
            db, league_id, season, snapshot_date, qualifying_minutes
        )
        # Idempotent upsert: delete existing rows for this computed_date
        # + league first, then insert all fresh rows (§2 B2).
        (
            db.query(EmergingPlayerScore)
            .filter(
                EmergingPlayerScore.league_id == league_id,
                EmergingPlayerScore.computed_date == snapshot_date,
            )
            .delete(synchronize_session=False)
        )
        for entry in scores:
            db.add(
                EmergingPlayerScore(
                    player_id=entry["player_id"],
                    league_id=league_id,
                    computed_date=snapshot_date,
                    score=entry["score"],
                    contributing_factors=entry["factors"],
                )
            )
            written += 1

    db.commit()
    return written


def _score_league(
    db: Session,
    league_id: int,
    season: str,
    snapshot_date: datetime,
    qualifying_minutes: float,
) -> list[dict[str, Any]]:
    """Score all eligible players in one league."""
    # Get qualifying players: latest snapshot per player in this league+season
    # with minutes >= threshold.
    snaps = (
        db.query(StatSnapshot)
        .filter(
            StatSnapshot.league_id == league_id,
            StatSnapshot.season == season,
            StatSnapshot.minutes_played >= qualifying_minutes,
        )
        .order_by(StatSnapshot.scrape_date.desc(), StatSnapshot.player_id)
        .all()
    )
    # Keep latest snapshot per player.
    latest: dict[int, StatSnapshot] = {}
    for snap in snaps:
        latest.setdefault(snap.player_id, snap)

    if not latest:
        return []

    player_ids = list(latest.keys())
    players = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    # Get published percentile rows for these players (all metrics).
    pct_rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.percentile_value.isnot(None),
            StatSnapshot.player_id.in_(player_ids),
            StatSnapshot.league_id == league_id,
            StatSnapshot.season == season,
        )
        .all()
    )

    # Group percentile values by player and metric, ordered by snapshot date.
    # We need the trend window: last TREND_WINDOW dates per player per metric.
    from collections import defaultdict

    player_metrics: dict[int, dict[str, list[tuple[datetime, float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for pct, snap in pct_rows:
        val = pct.percentile_value
        if val is None:
            continue
        player_metrics[snap.player_id][pct.metric_name].append(
            (snap.scrape_date, val)
        )

    # Sort each metric's points by date.
    for pid in player_metrics:
        for metric in player_metrics[pid]:
            player_metrics[pid][metric].sort(key=lambda x: x[0])

    # Score each player.
    results: list[dict[str, Any]] = []
    for pid, snap in latest.items():
        player = players.get(pid)
        if player is None:
            continue

        metrics_data = player_metrics.get(pid, {})
        if len(metrics_data) < MIN_METRICS_FOR_TREND:
            continue

        # Get the last TREND_WINDOW snapshot dates for this player.
        all_dates = sorted(
            {d for pts in metrics_data.values() for d, _ in pts}
        )
        if len(all_dates) < MIN_SNAPSHOTS:
            continue

        window_dates = all_dates[-TREND_WINDOW:]

        # 1. Trend magnitude: average percentile improvement across metrics.
        improvements = []
        for metric, points in metrics_data.items():
            # Get first and last values within the window.
            window_points = [(d, v) for d, v in points if d in set(window_dates)]
            if len(window_points) < 2:
                continue
            first_val = window_points[0][1]
            last_val = window_points[-1][1]
            improvement = max(last_val - first_val, 0)
            improvements.append(improvement)

        if not improvements:
            continue

        trend_magnitude = sum(improvements) / len(improvements) / 100.0

        # 2. Trend consistency: fraction of metrics with sustained upward trend
        #    (positive in at least ceil(60% of window) points).
        consistent_count = 0
        total_metrics = 0
        min_positive = max(2, math.ceil(len(window_dates) * 0.6))
        for metric, points in metrics_data.items():
            window_points = [(d, v) for d, v in points if d in set(window_dates)]
            if len(window_points) < 2:
                continue
            total_metrics += 1
            values = [v for _, v in window_points]
            positive_count = sum(
                1 for i in range(1, len(values)) if values[i] > values[i - 1]
            )
            if positive_count >= min_positive:
                consistent_count += 1

        trend_consistency = consistent_count / total_metrics if total_metrics > 0 else 0.0

        # 3. Age weight: sigmoid centred at AGE_MIDPOINT.
        age = _player_age(player)
        if age is not None:
            age_weight = 1.0 / (1.0 + math.exp((age - AGE_MIDPOINT) / AGE_SCALE))
        else:
            age_weight = 0.50  # neutral when DOB is unknown

        # 4. Sample weight: minutes / qualifying_minutes, capped at 1.0.
        sample_weight = min(snap.minutes_played / qualifying_minutes, 1.0)

        # Composite score.
        score = (
            W_TREND_MAGNITUDE * trend_magnitude
            + W_TREND_CONSISTENCY * trend_consistency
            + W_AGE * age_weight
            + W_SAMPLE * sample_weight
        )

        # Only include players above the threshold.
        if score < SCORE_THRESHOLD:
            continue

        results.append(
            {
                "player_id": pid,
                "score": round(score, 4),
                "factors": {
                    "trend_magnitude": round(trend_magnitude, 4),
                    "trend_consistency": round(trend_consistency, 4),
                    "age_weight": round(age_weight, 4),
                    "sample_weight": round(sample_weight, 4),
                    "age": age,
                    "minutes": snap.minutes_played,
                    "metrics_tracked": len(improvements),
                    "window_dates": len(window_dates),
                },
            }
        )

    # Sort by score descending.
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def _player_age(player: Player) -> int | None:
    """Compute age in years from date_of_birth, or None if unavailable."""
    if player.date_of_birth is None:
        return None
    today = datetime.now(tz=timezone.utc).date()
    dob = player.date_of_birth
    # date_of_birth is a DATE column (date object).
    if isinstance(dob, datetime):
        dob = dob.date()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
