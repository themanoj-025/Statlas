"""Watch-trigger detection (Phase 10 — Part C).

Runs as the step AFTER percentile/index computation is published in
`orchestration/weekly_refresh.py`. For every active watch it compares the
newly-published snapshot (the `snapshot_date` being processed) against the
preceding published snapshot for the same entity and evaluates the trigger
types from docs/product/alert-trigger-definitions.md §2:

- `percentile_movement`  — |delta| >= ALERT_PERCENTILE_MOVE_THRESHOLD (default
  15, INCLUSIVE), both snapshots qualifying (>= qualifying_minutes), same
  metric, only watched metrics (broad default = position metric set)
- `club_change`          — team_id differs across the pair; fires ONCE per
  transition (keyed on the from/to/snapshot triple)
- `new_season_data`      — the new snapshot's season differs from the previous
  published season AND qualifies; fires ONCE per season (keyed on season)
- `data_coverage_change` — coverage_gained: the entity's PREVIOUS season had no
  statsbomb coverage for its league but the new season does; source_anomaly:
  an unresolved IngestionAnomaly was flagged for the entity this cycle

Idempotency: every alert carries a (watch_id, alert_type, dedupe_key) unique
key — re-running detection for an already-processed snapshot-date computes the
same keys and creates nothing (the unique constraint is the hard guarantee).
All `detail` values are pulled from the real snapshot/coverage/anomaly rows.

The entity data is loaded in BATCH queries (all watched players in two queries,
not N per watch) — the strategy documented in
docs/engineering/watch-detection-scaling-notes.md, implemented here at MVP
scale.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings, load_registry
from app.models import (
    DataCoverage,
    IngestionAnomaly,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
    Watch,
    WatchAlert,
)

logger = logging.getLogger(__name__)

ALERT_TYPE_PERCENTILE = "percentile_movement"
ALERT_TYPE_CLUB = "club_change"
ALERT_TYPE_NEW_SEASON = "new_season_data"
ALERT_TYPE_COVERAGE = "data_coverage_change"


@dataclass
class WatchDetectionReport:
    watches_evaluated: int = 0
    alerts_created: int = 0
    by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_alert(self, alert_type: str) -> None:
        self.alerts_created += 1
        self.by_type[alert_type] += 1


# ---------------------------------------------------------------------------
# Batch loading — all watched entities in a handful of queries
# ---------------------------------------------------------------------------


@dataclass
class EntitySummary:
    """One published snapshot's worth of watch-relevant data for an entity."""

    date: datetime
    season: str
    team_id: int | None = None
    league_id: int | None = None
    minutes: float = 0.0
    percentiles: dict[str, float] = field(default_factory=dict)


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; make them tz-aware UTC so comparisons
    against the (aware) snapshot_date are exact (timezone-policy.md)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _player_history(
    db: Session, player_ids: list[int], snapshot_date: datetime
) -> dict[int, list[EntitySummary]]:
    """For each watched player: the two most recent distinct published snapshot
    dates (<= snapshot_date) with their percentile vectors — two queries total
    for ALL watched players."""
    if not player_ids:
        return {}

    dates_q = (
        db.query(StatSnapshot.player_id, StatSnapshot.scrape_date)
        .join(
            PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id
        )
        .filter(
            StatSnapshot.player_id.in_(player_ids),
            StatSnapshot.scrape_date <= snapshot_date,
            PercentileSnapshot.is_published.is_(True),
        )
        .distinct()
        .order_by(StatSnapshot.player_id, StatSnapshot.scrape_date.desc())
        .all()
    )
    keep: dict[int, list[datetime]] = {}
    for pid, raw_date in dates_q:
        d = _as_utc(raw_date)
        if pid not in keep:
            keep[pid] = [d]
        elif len(keep[pid]) < 2:
            keep[pid].append(d)
    if not keep:
        return {}

    rows = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            StatSnapshot.player_id.in_(list(keep.keys())),
            StatSnapshot.scrape_date.in_([d for ds in keep.values() for d in ds]),
            PercentileSnapshot.is_published.is_(True),
        )
        .order_by(
            StatSnapshot.player_id, StatSnapshot.scrape_date, PercentileSnapshot.id
        )
        .all()
    )
    history: dict[int, dict[datetime, EntitySummary]] = {}
    for pct, snap in rows:
        date = _as_utc(snap.scrape_date)
        summary = history.setdefault(snap.player_id, {}).setdefault(
            date,
            EntitySummary(
                date=date,
                season=snap.season,
                team_id=snap.team_id,
                league_id=snap.league_id,
                minutes=snap.minutes_played or 0.0,
            ),
        )
        if pct.metric_name != "si_index" and pct.percentile_value is not None:
            summary.percentiles[pct.metric_name] = pct.percentile_value
    return {
        pid: sorted(dates_by_date.items(), key=lambda kv: kv[0], reverse=True)
        for pid, dates_by_date in history.items()
    }


def _team_seasons(
    db: Session, team_ids: list[int]
) -> dict[int, list[tuple[str, datetime]]]:
    """For each watched team: distinct seasons among the team's snapshots with
    the season's earliest snapshot date (newest season first)."""
    if not team_ids:
        return {}
    rows = (
        db.query(StatSnapshot.team_id, StatSnapshot.season, StatSnapshot.scrape_date)
        .filter(StatSnapshot.team_id.in_(team_ids))
        .all()
    )
    by_team: dict[int, dict[str, datetime]] = defaultdict(dict)
    for team_id, season, scrape_date in rows:
        date = _as_utc(scrape_date)
        existing = by_team[team_id].get(season)
        if existing is None or date < existing:
            by_team[team_id][season] = date
    return {
        team_id: sorted(seasons.items(), key=lambda kv: kv[1], reverse=True)
        for team_id, seasons in by_team.items()
    }


def _statsbomb_league_seasons(
    db: Session, league_ids: list[int]
) -> dict[int, set[str]]:
    """League id -> set of seasons with an ACTIVE statsbomb coverage row."""
    if not league_ids:
        return {}
    rows = (
        db.query(DataCoverage)
        .filter(
            DataCoverage.source == "statsbomb",
            DataCoverage.status == "active",
            DataCoverage.league_id.in_(league_ids),
        )
        .all()
    )
    return {row.league_id: set(row.seasons_available or []) for row in rows}


def _unresolved_anomaly_count(
    db: Session, player_ids: list[int], snapshot_date: datetime
) -> dict[int, int]:
    """Player id -> count of unresolved anomalies on this cycle's snapshots."""
    if not player_ids:
        return {}
    rows = (
        db.query(IngestionAnomaly, StatSnapshot)
        .join(StatSnapshot, IngestionAnomaly.stat_snapshot_id == StatSnapshot.id)
        .filter(
            StatSnapshot.player_id.in_(player_ids),
            StatSnapshot.scrape_date == snapshot_date,
            IngestionAnomaly.resolved.is_(False),
        )
        .all()
    )
    counts: dict[int, int] = defaultdict(int)
    for _anomaly, snap in rows:
        counts[snap.player_id] += 1
    return counts


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------


def _position_metrics(position_group: str | None) -> list[str]:
    registry = load_registry()
    if position_group == "GK":
        return list(registry["gk_metrics"])
    return list(registry["outfield_metrics"])


def _try_insert_alert(
    db: Session, watch: Watch, alert_type: str, dedupe_key: str, detail: dict[str, Any]
) -> bool:
    """Insert one alert idempotently. Returns True when a NEW row was created;
    False when the (watch, type, key) already exists (a re-run or a duplicate
    detection — never a second alert)."""
    existing = (
        db.query(WatchAlert.id)
        .filter(
            WatchAlert.watch_id == watch.id,
            WatchAlert.alert_type == alert_type,
            WatchAlert.dedupe_key == dedupe_key,
        )
        .first()
    )
    if existing is not None:
        return False
    db.add(
        WatchAlert(
            watch_id=watch.id,
            alert_type=alert_type,
            dedupe_key=dedupe_key,
            detail=detail,
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()  # unique constraint — another run inserted it first
        return False
    return True


def _evaluate_player(
    db: Session,
    watch: Watch,
    history: list[tuple[datetime, EntitySummary]],
    *,
    snapshot_date: datetime,
    qualifying_minutes: float,
    threshold: float,
    coverage_seasons: dict[int, set[str]],
    anomaly_counts: dict[int, int],
    report: WatchDetectionReport,
) -> None:
    """Evaluate every trigger type for one watched player against the pair
    (previous published snapshot, this cycle's snapshot)."""
    # history is newest-first; the pair is [1] (previous) -> [0] (current).
    if len(history) < 2:
        return
    prev_date, prev = history[1]
    curr_date, curr = history[0]

    # Only evaluate the snapshot being processed this cycle — a user who
    # follows a player AFTER an event happened gets no historical alert.
    if curr_date != snapshot_date:
        return

    # --- percentile_movement -------------------------------------------------
    player = db.get(Player, watch.entity_id)
    if watch.followed_metrics:
        metrics = watch.followed_metrics
    else:
        metrics = _position_metrics(player.position_group if player else None)
    prev_qualifying = prev.minutes >= qualifying_minutes
    curr_qualifying = curr.minutes >= qualifying_minutes
    if prev_qualifying and curr_qualifying:
        for metric in metrics:
            fp = prev.percentiles.get(metric)
            tp = curr.percentiles.get(metric)
            if fp is None or tp is None:
                continue  # missing data for either snapshot — never guess
            if abs(tp - fp) >= threshold and _try_insert_alert(
                db,
                watch,
                ALERT_TYPE_PERCENTILE,
                dedupe_key=f"{metric}:{_iso(prev_date)}:{_iso(curr_date)}",
                detail={
                    "metric": metric,
                    "metric_name": _metric_name(metric),
                    "from_percentile": fp,
                    "to_percentile": tp,
                    "from_snapshot_date": _iso(prev_date),
                    "to_snapshot_date": _iso(curr_date),
                    "from_minutes": prev.minutes,
                    "to_minutes": curr.minutes,
                    "from_league": _league_name(db, prev.league_id),
                    "to_league": _league_name(db, curr.league_id),
                    "entity_name": player.canonical_name if player else None,
                },
            ):
                report.add_alert(ALERT_TYPE_PERCENTILE)

    # --- club_change ---------------------------------------------------------
    if (
        prev.team_id is not None
        and curr.team_id is not None
        and prev.team_id != curr.team_id
    ):
        player = db.get(Player, watch.entity_id)
        from_team = db.get(Team, prev.team_id)
        to_team = db.get(Team, curr.team_id)
        if _try_insert_alert(
            db,
            watch,
            ALERT_TYPE_CLUB,
            dedupe_key=f"{prev.team_id}:{curr.team_id}:{_iso(curr_date)}",
            detail={
                "from_team": from_team.name if from_team else None,
                "from_team_id": prev.team_id,
                "to_team": to_team.name if to_team else None,
                "to_team_id": curr.team_id,
                "snapshot_date": _iso(curr_date),
                "from_league": _league_name(db, prev.league_id),
                "to_league": _league_name(db, curr.league_id),
                "entity_name": player.canonical_name if player else None,
            },
        ):
            report.add_alert(ALERT_TYPE_CLUB)

    # --- new_season_data ------------------------------------------------------
    if prev.season != curr.season and curr.minutes >= qualifying_minutes:
        player = db.get(Player, watch.entity_id)
        if _try_insert_alert(
            db,
            watch,
            ALERT_TYPE_NEW_SEASON,
            dedupe_key=f"season:{curr.season}",
            detail={
                "new_season": curr.season,
                "previous_season": prev.season,
                "snapshot_date": _iso(curr_date),
                "entity_type": "player",
                "entity_name": player.canonical_name if player else None,
            },
        ):
            report.add_alert(ALERT_TYPE_NEW_SEASON)

    # --- data_coverage_change -------------------------------------------------
    league_id = curr.league_id
    if league_id is not None:
        prev_covered = (
            prev.league_id in coverage_seasons
            and prev.season in coverage_seasons[prev.league_id]
        )
        curr_covered = (
            league_id in coverage_seasons and curr.season in coverage_seasons[league_id]
        )
        if not prev_covered and curr_covered:
            player = db.get(Player, watch.entity_id)
            if _try_insert_alert(
                db,
                watch,
                ALERT_TYPE_COVERAGE,
                dedupe_key=f"coverage:{league_id}:{curr.season}",
                detail={
                    "signal": "coverage_gained",
                    "league": _league_name(db, league_id),
                    "season": curr.season,
                    "coverage_source": "statsbomb",
                    "entity_type": "player",
                    "entity_name": player.canonical_name if player else None,
                },
            ):
                report.add_alert(ALERT_TYPE_COVERAGE)

    # --- source_anomaly --------------------------------------------------------
    anomaly_count = anomaly_counts.get(watch.entity_id, 0)
    if anomaly_count:
        player = db.get(Player, watch.entity_id)
        if _try_insert_alert(
            db,
            watch,
            ALERT_TYPE_COVERAGE,
            dedupe_key=f"anomaly:{_iso(curr_date)}",
            detail={
                "signal": "source_anomaly",
                "anomaly_count": anomaly_count,
                "snapshot_date": _iso(curr_date),
                "entity_type": "player",
                "entity_name": player.canonical_name if player else None,
            },
        ):
            report.add_alert(ALERT_TYPE_COVERAGE)


def _evaluate_team(
    db: Session,
    watch: Watch,
    team_seasons: list[tuple[str, datetime]],
    *,
    snapshot_date: datetime,
    coverage_seasons: dict[int, set[str]],
    report: WatchDetectionReport,
) -> None:
    """Team triggers: new-season arrival and coverage gain. Teams have no
    percentile vector, so percentile/club triggers are player-only by
    construction (alert-trigger-definitions.md §2)."""
    team = db.get(Team, watch.entity_id)
    if team is None or len(team_seasons) < 1:
        return
    curr_season, curr_first_date = team_seasons[0]
    prev_season = team_seasons[1][0] if len(team_seasons) > 1 else None

    # --- new_season_data: the season's FIRST snapshot arrived this cycle ------
    if (
        prev_season is not None
        and curr_season != prev_season
        and curr_first_date == snapshot_date
    ) and _try_insert_alert(
        db,
        watch,
        ALERT_TYPE_NEW_SEASON,
        dedupe_key=f"season:{curr_season}",
        detail={
            "new_season": curr_season,
            "previous_season": prev_season,
            "snapshot_date": _iso(curr_first_date),
            "entity_type": "team",
            "entity_name": team.name,
        },
    ):
        report.add_alert(ALERT_TYPE_NEW_SEASON)

    # --- data_coverage_change --------------------------------------------------
    league_id = team.league_id
    if league_id is not None:
        prev_covered = (
            prev_season is not None
            and league_id in coverage_seasons
            and prev_season in coverage_seasons[league_id]
        )
        curr_covered = (
            league_id in coverage_seasons and curr_season in coverage_seasons[league_id]
        )
        if not prev_covered and curr_covered and _try_insert_alert(
            db,
            watch,
            ALERT_TYPE_COVERAGE,
            dedupe_key=f"coverage:{league_id}:{curr_season}",
            detail={
                "signal": "coverage_gained",
                "league": _league_name(db, league_id),
                "season": curr_season,
                "coverage_source": "statsbomb",
                "entity_type": "team",
                "entity_name": team.name,
            },
        ):
            report.add_alert(ALERT_TYPE_COVERAGE)


# ---------------------------------------------------------------------------
# The job
# ---------------------------------------------------------------------------


def detect_watch_triggers(
    db: Session,
    snapshot_date: datetime,
    *,
    now: datetime | None = None,
    threshold: float | None = None,
    qualifying_minutes: float | None = None,
) -> WatchDetectionReport:
    """Evaluate every active watch against the freshly-published snapshot.

    Called by run_weekly_refresh AFTER publish. Idempotent: re-running for an
    already-processed snapshot-date creates no duplicate alerts (dedupe keys +
    the unique constraint). `threshold`/`qualifying_minutes` are injectable for
    tests; defaults come from config + the Metric Registry.
    """
    report = WatchDetectionReport()
    settings = get_settings()
    threshold = (
        threshold if threshold is not None else settings.alert_percentile_move_threshold
    )
    qualifying_minutes = (
        qualifying_minutes
        if qualifying_minutes is not None
        else float(load_registry()["qualifying_minutes"])
    )

    watches = db.query(Watch).all()
    if not watches:
        return report
    report.watches_evaluated = len(watches)

    player_ids = [w.entity_id for w in watches if w.entity_type == "player"]
    team_ids = [w.entity_id for w in watches if w.entity_type == "team"]

    player_history = _player_history(db, player_ids, snapshot_date)
    team_seasons = _team_seasons(db, team_ids)

    # League coverage (statsbomb) + unresolved anomalies — one query each.
    league_ids = set()
    for summary_list in player_history.values():
        for _d, s in summary_list:
            if s.league_id is not None:
                league_ids.add(s.league_id)
    for team in (db.get(Team, tid) for tid in team_ids):
        if team is not None and team.league_id is not None:
            league_ids.add(team.league_id)
    coverage_seasons = _statsbomb_league_seasons(db, list(league_ids))
    anomaly_counts = _unresolved_anomaly_count(db, player_ids, snapshot_date)

    for watch in watches:
        if watch.entity_type == "player":
            history = player_history.get(watch.entity_id, [])
            _evaluate_player(
                db,
                watch,
                history,
                snapshot_date=snapshot_date,
                qualifying_minutes=qualifying_minutes,
                threshold=threshold,
                coverage_seasons=coverage_seasons,
                anomaly_counts=anomaly_counts,
                report=report,
            )
        else:
            _evaluate_team(
                db,
                watch,
                team_seasons.get(watch.entity_id, []),
                snapshot_date=snapshot_date,
                coverage_seasons=coverage_seasons,
                report=report,
            )

    db.commit()
    return report


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _iso(value: datetime) -> str:
    return value.date().isoformat() if hasattr(value, "date") else str(value)[:10]


def _metric_name(metric: str) -> str:
    registry = load_registry()
    meta = registry["metrics"].get(metric)
    return meta["name"] if meta else metric


def _league_name(db: Session, league_id: int | None) -> str | None:
    if league_id is None:
        return None
    from app.models import League

    league = db.get(League, league_id)
    return league.name if league else None
