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

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default to SQLite dev.db for local runs; override with DATABASE_URL env var.
os.environ.setdefault(
    "DATABASE_URL", f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'dev.db'}"
)

from app.config import CURRENT_SEASON, get_settings, load_tiers  # noqa: E402
from app.db import create_schema, session_scope  # noqa: E402

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
            print(f"\n  Failures:")
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
        except Exception as exc:
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
            except Exception as exc:
                print(f"  {slug} (FBRef): FAILED -- {exc}")
            league_cfg = tiers_cfg["leagues"].get(slug, {})
            if league_cfg.get("tier") == "tier_1":
                try:
                    u_records = understat.fetch_league_stats(slug, season)
                    print(f"  {slug} (Understat): {len(u_records)} players")
                except Exception as exc:
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
    elapsed = time.monotonic() - t0

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
    except Exception as exc:
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
        except Exception as exc:
            print(f"  FAIL {cname}: {exc}")

    print(f"\n  Total: {total['matches']} matches, {total['events']} events")
    return total


# ---------------------------------------------------------------------------
# Multi-season backfill engine
# ---------------------------------------------------------------------------

def run_backfill(
    seasons: list[str],
    league_slugs: list[str] | None = None,
    *,
    do_statsbomb: bool = False,
    require_tier_completeness: bool = False,
) -> int:
    """Run ingestion across multiple seasons with progress tracking.

    Each league-season combination is tracked independently. If the script
    is interrupted, running again with --resume skips completed tasks.
    """
    tiers_cfg = load_tiers()
    all_leagues = league_slugs or list(tiers_cfg["leagues"].keys())
    total_tasks = len(seasons) * len(all_leagues)

    tracker = ProgressTracker()
    tracker.start_run(seasons, all_leagues)

    # Count already done
    already_done = sum(
        1
        for s in seasons
        for l in all_leagues
        if tracker.is_completed(s, l)
    )
    remaining = total_tasks - already_done

    _print_section("Multi-Season Backfill")
    print(f"  Seasons:     {len(seasons)} ({seasons[0]} to {seasons[-1]})")
    print(f"  Leagues:     {len(all_leagues)}")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Already done: {already_done}")
    print(f"  Remaining:   {remaining}")
    if remaining == 0:
        print("\n  All tasks already completed. Use --reset-progress to re-run.")
        return 0
    print(f"  Estimated:   {_estimate_time(remaining)}")
    print()

    run_start = time.monotonic()
    tasks_completed = 0
    total_snapshots = 0
    total_errors = 0

    for s_idx, season in enumerate(seasons, 1):
        for l_idx, league in enumerate(all_leagues, 1):
            # Skip completed
            if tracker.is_completed(season, league):
                continue

            elapsed = time.monotonic() - run_start
            _progress_line(
                s_idx, len(seasons),
                l_idx, len(all_leagues),
                season, league,
                elapsed, tasks_completed, remaining,
            )

            t0 = time.monotonic()
            try:
                with session_scope() as db:
                    report = ingest_season(
                        db,
                        season,
                        league_slugs=[league],
                        do_statsbomb=do_statsbomb,
                        require_tier_completeness=require_tier_completeness,
                    )
                league_elapsed = time.monotonic() - t0
                snaps = report.snapshots_inserted if report else 0
                errs = len(report.errors) if report else 0
                total_snapshots += snaps
                total_errors += errs
                tracker.mark_completed(season, league, snapshots=snaps, elapsed=league_elapsed)
                tasks_completed += 1
                status = "ok" if errs == 0 else f"{errs} errors"
                print(
                    f"\r  [OK] {season}/{league}: "
                    f"{snaps} snapshots, {league_elapsed:.0f}s -- {status}       "
                )
            except Exception as exc:
                league_elapsed = time.monotonic() - t0
                tracker.mark_failed(season, league, str(exc))
                tasks_completed += 1
                total_errors += 1
                print(
                    f"\r  [FAIL] {season}/{league}: {str(exc)[:60]}       "
                )

    # Final summary
    total_elapsed = time.monotonic() - run_start
    summary = tracker.get_summary()

    _print_section("Backfill Complete")
    print(f"  Total time:    {_format_eta(total_elapsed)}")
    print(f"  Seasons:       {len(seasons)}")
    print(f"  Leagues:       {len(all_leagues)}")
    print(f"  Completed:     {summary['completed']}")
    print(f"  Failed:        {summary['failed']}")
    print(f"  Snapshots:     {summary['total_snapshots']}")
    print(f"  Errors:        {total_errors}")
    if summary["completed"] > 0:
        avg = total_elapsed / summary["completed"]
        print(f"  Avg per task:  {avg:.0f}s")
    print(f"  Progress file: {PROGRESS_FILE}")

    return 0 if total_errors == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest_real_data",
        description="Download real football data and seed the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill all seasons 2017-2026
  %(prog)s --start-from 2017-18

  # Resume an interrupted backfill
  %(prog)s --resume

  # Check progress
  %(prog)s --status

  # Fetch specific seasons
  %(prog)s --seasons 2023-24,2024-25,2025-26

  # Single season, specific leagues
  %(prog)s --season 2025-26 --leagues premier-league,la-liga

  # Reset and start fresh from 2020
  %(prog)s --reset-progress --start-from 2020-21

  # Dry-run
  %(prog)s --season 2025-26 --dry-run
        """,
    )

    # -- Mode flags (mutually exclusive) ---
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted backfill (skips completed season/league combos).",
    )
    mode.add_argument(
        "--status",
        action="store_true",
        help="Show current ingestion progress and exit.",
    )
    mode.add_argument(
        "--reset-progress",
        action="store_true",
        help="Delete progress file and start fresh.",
    )

    # -- Season selection ---
    parser.add_argument(
        "--season",
        default=None,
        help="Single season to fetch (e.g. 2025-26).",
    )
    parser.add_argument(
        "--seasons",
        default=None,
        help="Comma-separated seasons (e.g. 2023-24,2024-25,2025-26).",
    )
    parser.add_argument(
        "--start-from",
        default=None,
        metavar="SEASON",
        help="Start backfill from this season through the current season "
             "(e.g. --start-from 2017-18 fetches 2017-18 through 2025-26).",
    )

    # -- League selection ---
    parser.add_argument(
        "--leagues",
        default=None,
        help="Comma-separated league slugs (default: all 19 leagues).",
    )

    # -- Options ---
    parser.add_argument(
        "--statsbomb",
        action="store_true",
        help="Also sync StatsBomb open event data.",
    )
    parser.add_argument(
        "--statsbomb-only",
        action="store_true",
        help="Only sync StatsBomb events.",
    )
    parser.add_argument(
        "--max-competitions",
        type=int,
        default=None,
        help="Max StatsBomb competitions to sync.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print without writing to DB.",
    )
    parser.add_argument(
        "--require-tier-completeness",
        action="store_true",
        help="Withhold tier percentiles until all leagues are ingested.",
    )
    parser.add_argument(
        "--dataset-mode",
        choices=["fixture-demo", "production"],
        default=None,
        help="Override STATLAS_DATASET_MODE.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Debug logging.",
    )
    return parser.parse_args()


def _resolve_seasons(args: argparse.Namespace) -> list[str]:
    """Resolve which seasons to fetch from CLI args."""
    if args.start_from:
        start = args.start_from
        # Generate seasons from start through current
        start_year = int(start.split("-")[0])
        current_year = int(CURRENT_SEASON.split("-")[0])
        return [f"{y}-{str(y + 1)[-2:]}" for y in range(start_year, current_year + 1)]
    if args.seasons:
        return [s.strip() for s in args.seasons.split(",")]
    if args.season:
        return [args.season]
    return [CURRENT_SEASON]


def main() -> int:
    args = parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Dataset mode override
    if args.dataset_mode:
        os.environ["STATLAS_DATASET_MODE"] = args.dataset_mode

    # Resolve league slugs
    league_slugs = None
    if args.leagues:
        league_slugs = [s.strip() for s in args.leagues.split(",")]

    tiers_cfg = load_tiers()
    all_leagues = league_slugs or list(tiers_cfg["leagues"].keys())

    # -- Status mode ---
    if args.status:
        tracker = ProgressTracker()
        seasons = _resolve_seasons(args)
        tracker.print_status(seasons, all_leagues)
        return 0

    # -- Reset progress ---
    if args.reset_progress:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
            print(f"  Deleted {PROGRESS_FILE}")
        else:
            print("  No progress file to delete.")
        if not args.resume and not args.start_from and not args.seasons and not args.season:
            return 0

    # -- Resume mode ---
    if args.resume:
        tracker = ProgressTracker()
        if not tracker._state.get("config"):
            print("  No previous run found. Use --start-from to begin a new backfill.")
            return 1
        seasons = tracker._state["config"]["seasons"]
        all_leagues = tracker._state["config"]["leagues"]
        if args.leagues:
            all_leagues = league_slugs
        print(f"  Resuming: {len(seasons)} seasons x {len(all_leagues)} leagues")
        create_schema()
        return run_backfill(
            seasons,
            all_leagues,
            do_statsbomb=args.statsbomb,
            require_tier_completeness=args.require_tier_completeness,
        )

    # -- Resolve seasons ---
    seasons = _resolve_seasons(args)

    # -- StatsBomb-only mode ---
    if args.statsbomb_only:
        if args.dry_run:
            print("\n  --dry-run is not supported for --statsbomb-only mode")
            return 1
        create_schema()
        with session_scope() as db:
            sync_statsbomb_events(db, max_competitions=args.max_competitions)
        return 0

    # -- Dry-run mode ---
    if args.dry_run:
        for season in seasons:
            with session_scope() as db:
                ingest_season(
                    db,
                    season,
                    league_slugs=league_slugs,
                    do_statsbomb=False,
                    dry_run=True,
                )
        return 0

    # -- Multi-season backfill ---
    if len(seasons) > 1:
        create_schema()
        return run_backfill(
            seasons,
            league_slugs,
            do_statsbomb=args.statsbomb,
            require_tier_completeness=args.require_tier_completeness,
        )

    # -- Single-season mode ---
    season = seasons[0]
    _print_section("Statlas Real-Data Ingestion")
    print(f"  Season:  {season}")
    if league_slugs:
        print(f"  Leagues: {', '.join(league_slugs)}")
    else:
        print(f"  Leagues: all ({len(all_leagues)} leagues)")
    sb_label = "yes" if args.statsbomb or args.statsbomb_only else "no"
    print(f"  StatsBomb: {sb_label}")
    db_url = get_settings().database_url or "SQLite (data/dev.db)"
    print(f"  Database: {db_url}")
    if get_settings().dataset_mode == "fixture-demo":
        print()
        print("  WARN Dataset mode is 'fixture-demo'. After the first real scrape:")
        print("    STATLAS_DATASET_MODE=production python scripts/ingest_real_data.py ...")

    create_schema()

    with session_scope() as db:
        report = ingest_season(
            db,
            season,
            league_slugs=league_slugs,
            do_statsbomb=args.statsbomb,
            require_tier_completeness=args.require_tier_completeness,
        )

    if args.statsbomb:
        with session_scope() as db:
            sync_statsbomb_events(db, max_competitions=args.max_competitions)

    if get_settings().dataset_mode == "fixture-demo":
        print(f"\n{'=' * 60}")
        print("  NEXT STEP: Switch to production dataset mode")
        print(f"  {'-' * 58}")
        print("  export STATLAS_DATASET_MODE=production")
        print("  # Then restart the API server to serve real data")
        print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
