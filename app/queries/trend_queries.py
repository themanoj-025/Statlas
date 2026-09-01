"""Trend / time-series queries (Phase 3 — Part A).

The trend feature reads the VERSIONED `stat_snapshots` table — the payoff for
Phase 1's append-only, dated-snapshot design. One snapshot per (player, team,
league, season, source, scrape_date); a trend is the sequence of those dates.

Honesty rules implemented here (Constitution §3, Never-List #11/#12):

- Granularity: trends are computed from the available snapshot history, which
  for the Phase 1 pipeline is weekly-scrape granularity — NOT per-match data.
  The response carries `granularity="snapshot"` and an explicit note; a chart
  never implies match-by-match precision.
- Gaps: when the player is missing a scrape date that their league/season
  calendar has (injury, scrape failure, no value for the metric), the response
  marks `gap_after` on the preceding point and lists the gap ranges. The UI
  renders a dashed segment / explicit break — never a false interpolation.
- Anomalies: a point whose winning snapshot is flagged (unresolved
  ingestion_anomaly) is marked `anomaly=true` so the UI can call it out.
- Immutability: this module only reads; it never mutates or "fixes" a snapshot.

Value resolution honours the registry's per-metric source precedence per date
(the same `resolve_metric_value` the percentile job uses), so a Tier-1 xG
trend reads Understat where the registry says Understat wins.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.compute.percentiles import resolve_metric_value
from app.config import load_registry
from app.models import PercentileSnapshot, Player, StatSnapshot, Team

TREND_WINDOWS = (5, 10)
DEFAULT_WINDOW = 5
MIN_TREND_SNAPSHOTS = 5  # honest floor: fewer and the trend is not meaningful

GRANULARITY_NOTE = (
    "Trends are computed from the weekly snapshot history in the database — "
    "snapshot granularity, not per-match data. Each point is one scrape date."
)


def _validate_window(window: int) -> int:
    if window not in TREND_WINDOWS:
        raise ValueError(f"window must be one of {list(TREND_WINDOWS)}")
    return window


def get_player_trend(
    db: Session,
    player_id: int,
    metric: str,
    *,
    window: int = DEFAULT_WINDOW,
) -> dict[str, Any] | None -> None:
    """Rolling snapshot-history trend for one player + one metric.

    Returns the last `window` scrape dates (oldest to newest) with per-date
    raw and percentile values, gap spans, and derived events (transfers), or
    None when the player does not exist.
    """
    registry = load_registry()
    spec = registry["metrics"].get(metric)
    if spec is None:
        raise ValueError(f"unknown metric '{metric}'")
    window = _validate_window(window)

    player = db.get(Player, player_id)
    if player is None:
        return None

    snaps = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.player_id == player_id)
        .order_by(StatSnapshot.scrape_date.asc())
        .all()
    )
    if not snaps:
        return {
            "player_id": player_id,
            "player_name": player.canonical_name,
            "metric": _metric_meta(registry, metric),
            "window": window,
            "granularity": "snapshot",
            "granularity_note": GRANULARITY_NOTE,
            "min_snapshots": MIN_TREND_SNAPSHOTS,
            "available": 0,
            "insufficient": True,
            "points": [],
            "gaps": [],
            "events": [],
        }

    latest = snaps[-1]
    league_id = latest.league_id
    season = latest.season

    # Cohort calendar: every date the pipeline scraped this player's
    # league+season (fbref AND understat — the winning source for a metric may
    # be either). Gaps are measured against THIS calendar, never invented.
    cohort_dates = {
        row[0].replace(tzinfo=None)
        for row in db.query(StatSnapshot.scrape_date)
        .filter(StatSnapshot.league_id == league_id, StatSnapshot.season == season)
        .distinct()
        .all()
    }

    # Group the player's snapshots by date, then resolve one value per date
    # using the registry precedence (per-metric, per-tier). Grouping keys are
    # normalised to UTC and then the tzinfo is dropped EXPLICITLY for the dict
    # key comparison (timezone-policy.md §5) — the values keep their zone.
    by_date: dict[datetime, dict[tuple[int, str], StatSnapshot]] = {}
    for snap in snaps:
        value = snap.scrape_date
        # Normalise tz-aware values to UTC (timezone-policy.md §5); SQLite
        # returns naive values (no tz column), which are already UTC by
        # convention — astimezone on a naive value would misread local time.
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        key = value.replace(tzinfo=None)
        by_date.setdefault(key, {})[(snap.player_id, snap.source)] = snap

    team_names = {t.id: t.name for t in db.query(Team).all()}
    tier = latest.league.tier if latest.league else None

    # Published percentile rows for this player + metric (the anomaly gate:
    # only is_published rows are queryable).
    pct_by_snapshot: dict[int, float] = {
        row.stat_snapshot_id: row.percentile_value
        for row in db.query(PercentileSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            StatSnapshot.player_id == player_id,
            PercentileSnapshot.metric_name == metric,
            PercentileSnapshot.is_published.is_(True),
        )
        .all()
        if row.percentile_value is not None
    }

    points: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for date in sorted(by_date):
        winner, value = _resolve_date_value(
            db, registry, metric, tier, player_id, by_date[date], spec
        )
        if winner is None:
            continue
        team = team_names.get(winner.team_id) if winner.team_id else None
        points.append(
            {
                "date": date.isoformat(),
                "raw": value,
                "pct": pct_by_snapshot.get(winner.id),
                "team_id": winner.team_id,
                "team": team,
                "source": winner.source,
                "minutes": winner.minutes_played,
                "matches": winner.matches_played,
                "gap_after": False,
                "anomaly": winner.status == "flagged",
            }
        )

    # Rolling window: keep the last `window` value-dates.
    points = points[-window:]
    available = len(points)

    # Transfer + gap detection over the windowed points (real, derived from
    # data — never curated milestones).
    gaps: list[dict[str, Any]] = []
    for i, _point in enumerate(points):
        if i + 1 >= len(points):
            break
        missed = [
            d
            for d in cohort_dates
            if points[i]["date"] < _iso(d) < points[i + 1]["date"]
        ]
        if missed:
            points[i]["gap_after"] = True
            gaps.append(
                {
                    "from_date": points[i]["date"],
                    "to_date": points[i + 1]["date"],
                    "missed_dates": [_iso(d) for d in sorted(missed)],
                }
            )
        if points[i]["team_id"] != points[i + 1]["team_id"]:
            events.append(
                {
                    "date": points[i + 1]["date"],
                    "type": "transfer",
                    "team_from": points[i]["team"],
                    "team_to": points[i + 1]["team"],
                }
            )

    from app.queries.player_queries import get_player_profile

    profile = get_player_profile(db, player_id)
    return {
        "player_id": player_id,
        "player_name": player.canonical_name,
        "metric": _metric_meta(registry, metric),
        "window": window,
        "granularity": "snapshot",
        "granularity_note": GRANULARITY_NOTE,
        "min_snapshots": MIN_TREND_SNAPSHOTS,
        "available": available,
        "insufficient": available < MIN_TREND_SNAPSHOTS,
        "league": profile.get("current_team") if profile else None,
        "season": season,
        "points": points,
        "gaps": gaps,
        "events": events,
    }


def _resolve_date_value(
    db: Session,
    registry: dict[str, Any],
    metric: str,
    tier: str | None,
    player_id: int,
    by_source: dict[tuple[int, str], StatSnapshot],
    spec: dict[str, Any],
) -> tuple[StatSnapshot | None, float | None]:
    """Resolve (winning snapshot, value) for one date using registry precedence.

    Reuses compute.percentiles.resolve_metric_value so the trend shows exactly
    the values the percentile job would use for that metric/tier — one model
    per comparison, never a mix. When no source on this date carries the
    metric (or the display floor is unmet), the date yields no point.
    """
    if tier is None:
        return None, None
    value, winner = resolve_metric_value(player_id, metric, tier, by_source, registry)
    return winner, value


def _metric_meta(registry: dict[str, Any], metric: str) -> dict[str, Any]:
    from app.api.registry_view import metric_meta

    meta = metric_meta(registry, metric)
    return (
        meta
        if meta is not None
        else {"id": metric, "name": metric, "unit": "", "direction": ""}
    )


def _iso(dt: datetime) -> str:
    return dt.isoformat()
