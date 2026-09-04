
#!/usr/bin/env python3
"""Statlas real-data ingestion -- downloads live data from free sources and
seeds the database through the full pipeline.

Features:
  - Multi-season historical backfill (2017-2026)
  - Progress tracking with persistent state file
  - Resumability: interrupted runs pick up where they left off
  - ETA calculation based on actual elapsed time per league-season
  - Per-league error isolation: one failed league does not stop others

Sources used (all free, no API key required):
  - FBRef: per-90 stats for all 19 leagues (Big-5 + Tier 2 + Tier 3)
  - Understat: xG/xA supplement for the Big-5 (Tier 1) only
  - StatsBomb: open event data (shot/pass coordinates) from GitHub

Usage:
    # Backfill all seasons 2017-2026, all leagues (~4-6 hours)
    python scripts/ingest_real_data.py --start-from 2017-18

    # Resume an interrupted run
    python scripts/ingest_real_data.py --resume

    # Fetch specific seasons
    python scripts/ingest_real_data.py --seasons 2023-24,2024-25,2025-26

    # Check current progress
    python scripts/ingest_real_data.py --status

    # Reset progress and start fresh
    python scripts/ingest_real_data.py --reset-progress --start-from 2020-21

    # Dry-run: fetch and print without writing to DB
    python scripts/ingest_real_data.py --season 2025-26 --dry-run

Environment variables:
    DATABASE_URL             -- target database (default: SQLite at data/dev.db)
    STATLAS_LOG_LEVEL        -- logging verbosity (default: INFO)
    STATLAS_DATASET_MODE     -- set to "production" after first real scrape
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default to SQLite dev.db for local runs; override with DATABASE_URL env var.
os.environ.setdefault(
    "DATABASE_URL", f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'dev.db'}"
)

from app.config import load_tiers

logger = logging.getLogger("ingest")

PROGRESS_FILE = PROJECT_ROOT / "data" / "ingestion_progress.json"

# All seasons from 2017-18 to the current season.
ALL_SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2017, 2027)]


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

class ProgressTracker:
    """Persistent progress state for multi-season ingestion.

    State is saved to data/ingestion_progress.json after every league-season
    so interrupted runs can resume exactly where they left off.
    """

    def __init__(self) -> None:
        self._path = PROGRESS_FILE
        self._state: dict = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._state = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._state = {}
        if not self._state:
            self._state = {
                "version": 1,
                "started_at": None,
                "last_updated": None,
                "config": {"seasons": [], "leagues": []},
                "completed": {},
                "elapsed_seconds": 0.0,
            }

    def _save(self) -> None:
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def start_run(self, seasons: list[str], leagues: list[str]) -> None:
        """Initialize a new run. Updates config if seasons/leagues changed."""
        if not self._state.get("started_at"):
            self._state["started_at"] = datetime.now(timezone.utc).isoformat()
        # Always update config so --start-from / --leagues take effect
        self._state["config"] = {"seasons": seasons, "leagues": leagues}
        self._save()

    def is_completed(self, season: str, league: str) -> bool:
        return (
            self._state.get("completed", {})
            .get(season, {})
            .get(league, {})
            .get("status")
            == "ok"
        )

    def mark_completed(
        self, season: str, league: str, snapshots: int = 0, elapsed: float = 0.0
    ) -> None:
        completed = self._state.setdefault("completed", {})
        season_data = completed.setdefault(season, {})
        season_data[league] = {
            "status": "ok",
            "snapshots": snapshots,
            "elapsed_s": round(elapsed, 1),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self._state["elapsed_seconds"] = (
            self._state.get("elapsed_seconds", 0.0) + elapsed
        )
        self._save()

    def mark_failed(self, season: str, league: str, error: str) -> None:
        completed = self._state.setdefault("completed", {})
        season_data = completed.setdefault(season, {})
        season_data[league] = {
            "status": "error",
            "error": error[:200],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def get_summary(self) -> dict:
        completed = self._state.get("completed", {})
        ok_count = 0
        fail_count = 0
        total_snapshots = 0
        for season_data in completed.values():
            for league_data in season_data.values():
                if league_data.get("status") == "ok":
                    ok_count += 1
                    total_snapshots += league_data.get("snapshots", 0)
                else:
                    fail_count += 1
        return {
            "completed": ok_count,
            "failed": fail_count,
            "total_snapshots": total_snapshots,
            "elapsed_seconds": self._state.get("elapsed_seconds", 0.0),
        }

    def print_status(self, all_seasons: list[str], all_leagues: list[str]) -> None:
        completed = self._state.get("completed", {})
        summary = self.get_summary()
        total_tasks = len(all_seasons) * len(all_leagues)
        done = summary["completed"]
        failed = summary["failed"]
        remaining = total_tasks - done - failed

        print(f"\n{'=' * 60}")
        print("  INGESTION PROGRESS")
        print(f"{'=' * 60}")
        print(f"  Started:     {self._state.get('started_at', 'never')}")
        print(f"  Last update: {self._state.get('last_updated', 'never')}")
        print(f"  Elapsed:     {summary['elapsed_seconds'] / 60:.1f} min")
        print(f"  Seasons:     {len(all_seasons)} ({all_seasons[0]} to {all_seasons[-1]})")
        print(f"  Leagues:     {len(all_leagues)}")
        print(f"  Total tasks: {total_tasks} (season x league)")
        print(f"  Completed:   {done}")
        print(f"  Failed:      {failed}")
        print(f"  Remaining:   {remaining}")

        if done > 0:
            avg = summary["elapsed_seconds"] / done
            eta = avg * remaining
            print(f"  Avg/task:    {avg:.0f}s")
            print(f"  ETA:         {eta / 60:.0f} min ({eta / 3600:.1f} hrs)")

        # Show per-season breakdown
        print(f"\n  {'Season':<12s} {'Done':>5s} {'Fail':>5s} {'Snaps':>7s}")
        print(f"  {'-' * 34}")
        for season in all_seasons:
            season_data = completed.get(season, {})
            ok = sum(1 for v in season_data.values() if v.get("status") == "ok")
            fl = sum(1 for v in season_data.values() if v.get("status") != "ok")
            snaps = sum(v.get("snapshots", 0) for v in season_data.values() if v.get("status") == "ok")
            marker = " *" if ok == len(all_leagues) else ""
            print(f"  {season:<12s} {ok:>5d} {fl:>5d} {snaps:>7d}{marker}")

        # Show failures
        failures = []
        for season, sdata in completed.items():
            for league, ldata in sdata.items():
                if ldata.get("status") != "ok":
                    failures.append((season, league, ldata.get("error", "?")))
        if failures:
            print("\n  Failures:")
            for season, league, err in failures[:10]:
                print(f"    {season}/{league}: {err[:60]}")

        print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_time(n_tasks: int, avg_seconds: float = 12.0) -> str:
    """Human-readable ETA."""
    seconds = n_tasks * avg_seconds
    if seconds < 60:
        return f"~{seconds}s"
    minutes = int(seconds // 60)
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"~{hours}h {mins}m"
    return f"~{minutes}m"


def _format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{minutes}m"


def _print_section(title: str) -> None:
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_summary(report: object) -> None:
    """Print a human-readable summary of the RefreshReport."""
    print(f"\n{'-' * 60}")
    print("  RESULTS")
    print(f"{'-' * 60}")
    fields = [
        ("Leagues scraped", "leagues_scraped"),
        ("Records ingested", "records_ingested"),
        ("Snapshots inserted", "snapshots_inserted"),
        ("Snapshots skipped (existing)", "snapshots_existing"),
        ("Records unmatched", "records_unmatched"),
        ("Anomalies (bounds)", "anomalies_bounds"),
        ("Anomalies (cross-source)", "anomalies_cross_source"),
        ("Blocked players", "blocked_players"),
        ("Percentile rows", "percentile_rows"),
        ("Index rows", "index_rows"),
        ("Published rows", "published_rows"),
        ("Events linked", "events_linked"),
        ("Events unmatched", "events_unmatched"),
        ("Market valuations inserted", "market_valuations_inserted"),
        ("Emerging scores", "emerging_scores"),
    ]
    for label, attr in fields:
        val = getattr(report, attr, None)
        if val is None:
            continue
        if isinstance(val, list):
            if val:
                items = ", ".join(str(v) for v in val[:5])
                suffix = "..." if len(val) > 5 else ""
                print(f"  {label}: {len(val)} ({items}{suffix})")
        else:
            print(f"  {label}: {val}")
    if report.errors:
        print(f"\n  WARN Errors ({len(report.errors)}):")
        for err in report.errors[:10]:
            print(f"    - {err}")
        if len(report.errors) > 10:
            print(f"    ... and {len(report.errors) - 10} more")
    print(f"{'-' * 60}")


def _progress_line(
    season_idx: int,
    total_seasons: int,
    league_idx: int,
    total_leagues: int,
    season: str,
    league: str,
    elapsed_so_far: float,
    tasks_done: int,
    total_tasks: int,
) -> None:
    """Print a compact progress line."""
    pct = (tasks_done / total_tasks * 100) if total_tasks > 0 else 0
    avg = elapsed_so_far / tasks_done if tasks_done > 0 else 12.0
    remaining = (total_tasks - tasks_done) * avg
    eta = _format_eta(remaining)
    print(
        f"\r  [{pct:5.1f}%] S{season_idx}/{total_seasons} "
        f"L{league_idx}/{total_leagues} "
        f"{season}/{league} "
        f"ETA: {eta}   ",
        end="",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------

def ingest_season(
    db,
    season: str,
    *,
    league_slugs: list[str] | None = None,
    do_statsbomb: bool = False,
    require_tier_completeness: bool = False,
    dry_run: bool = False,
) -> object:
    """Run the full weekly-refresh pipeline for one season.

    Returns the RefreshReport for caller to inspect.
    """
    from app.orchestration.weekly_refresh import run_weekly_refresh
    from app.sources.fbref import FBrefSource
    from app.sources.understat import UnderstatSource

    snapshot_date = datetime.now(timezone.utc)
    tiers_cfg = load_tiers()
    target_slugs = league_slugs or list(tiers_cfg["leagues"].keys())

    fbref = FBrefSource()
    understat = UnderstatSource()

    statsbomb_source = None
    statsbomb_competitions = None
    if do_statsbomb:
        from app.sources.statsbomb import StatsBombOpenDataSource

        statsbomb_source = StatsBombOpenDataSource()
        try:
            statsbomb_competitions = statsbomb_source.fetch_competitions()
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            logger.warning("Could not fetch StatsBomb competitions: %s", exc)
            statsbomb_competitions = []

    if dry_run:
        _print_section(f"DRY RUN -- {season}")
        for slug in target_slugs:
            try:
                records = fbref.fetch_league_stats(slug, season)
                print(f"\n  {slug} (FBRef): {len(records)} players")
                for r in records[:3]:
                    print(f"    {r.player_name:30s} {r.team_name:20s} {r.minutes_played:6.0f} min")
                if len(records) > 3:
                    print(f"    ... and {len(records) - 3} more")
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                print(f"  {slug} (FBRef): FAILED -- {exc}")
            league_cfg = tiers_cfg["leagues"].get(slug, {})
            if league_cfg.get("tier") == "tier_1":
                try:
                    u_records = understat.fetch_league_stats(slug, season)
                    print(f"  {slug} (Understat): {len(u_records)} players")
                except (requests.RequestException, ValueError, KeyError, OSError) as exc:
                    print(f"  {slug} (Understat): FAILED -- {exc}")
        return None

    t0 = time.monotonic()
    report = run_weekly_refresh(
        db,
        season,
        snapshot_date=snapshot_date,
        league_slugs=target_slugs,
        fbref_source=fbref,
        understat_source=understat,
        statsbomb_source=statsbomb_source,
        statsbomb_competitions=statsbomb_competitions,
        do_statsbomb=do_statsbomb,
        require_tier_completeness=require_tier_completeness,
    )
    time.monotonic() - t0

    _print_summary(report)
    return report


# ---------------------------------------------------------------------------
# StatsBomb event sync
# ---------------------------------------------------------------------------

def sync_statsbomb_events(db, max_competitions: int | None = None) -> dict:
    """Sync StatsBomb open-data events (shot/pass coordinates)."""
    from app.sources.statsbomb import StatsBombOpenDataSource

    _print_section("StatsBomb Event Sync")
    source = StatsBombOpenDataSource()

    try:
        competitions = source.fetch_competitions()
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        logger.error("Failed to fetch StatsBomb competitions: %s", exc)
        return {"error": str(exc)}

    by_comp: dict[int, list] = {}
    for comp in competitions:
        cid = comp.get("competition_id")
        by_comp.setdefault(cid, []).append(comp)

    print(f"  Available competitions: {len(by_comp)}")
    for cid, comps in list(by_comp.items())[:10]:
        name = comps[0].get("competition_name", "?")
        seasons = [c.get("season_name", "?") for c in comps]
        seasons_display = ", ".join(seasons[:3])
        if len(seasons) > 3:
            seasons_display += "..."
        print(f"    [{cid}] {name}: {len(seasons)} seasons ({seasons_display})")

    total = {"matches": 0, "events": 0}
    count = 0
    for comp in competitions:
        if max_competitions and count >= max_competitions:
            break
        cname = comp.get("competition_name", "?")
        try:
            result = source.sync_competition(db, comp)
            total["matches"] += result.get("matches", 0)
            total["events"] += result.get("events", 0)
            count += 1
            print(f"  OK {cname}: {result.get('matches', 0)} matches, {result.get('events', 0)} events")
        except (requests.RequestException, ValueError, KeyError, OSError) as exc:
            print(f"  FAIL {cname}: {exc}")

    print(f"\n  Total: {total['matches']} matches, {total['events']} events")
    return total


