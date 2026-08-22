#!/usr/bin/env python3
"""Statlas real-data ingestion -- downloads live data from free sources and
seeds the database through the full pipeline.

Sources used (all free, no API key required):
  - FBRef: per-90 stats for all 19 leagues (Big-5 + Tier 2 + Tier 3)
  - Understat: xG/xA supplement for the Big-5 (Tier 1) only
  - StatsBomb: open event data (shot/pass coordinates) from GitHub

Rate limiting is enforced per the compliance posture:
  - FBRef: 1 req / 10s +/- 2s jitter
  - Understat: 1 req / 5s
  - StatsBomb: no strict limit (public GitHub CDN)

Usage:
    # Fetch the current season across all leagues (~25 min for FBRef alone)
    python scripts/ingest_real_data.py --season 2025-26

    # Fetch a specific set of leagues
    python scripts/ingest_real_data.py --season 2025-26 --leagues premier-league,la-liga

    # Fetch multiple seasons (historical backfill)
    python scripts/ingest_real_data.py --seasons 2023-24,2024-25,2025-26

    # Dry-run: fetch and print without writing to DB
    python scripts/ingest_real_data.py --season 2025-26 --dry-run

    # With StatsBomb event data (slower, fetches match-by-match)
    python scripts/ingest_real_data.py --season 2025-26 --statsbomb

    # Use a custom database URL
    DATABASE_URL=postgresql://... python scripts/ingest_real_data.py --season 2025-26

Environment variables:
    DATABASE_URL             -- target database (default: SQLite at data/dev.db)
    STATLAS_LOG_LEVEL        -- logging verbosity (default: INFO)
    STATLAS_DATASET_MODE     -- set to "production" after first real scrape
"""

from __future__ import annotations

import argparse
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

from app.config import get_settings, load_tiers  # noqa: E402
from app.db import create_schema, session_scope  # noqa: E402

logger = logging.getLogger("ingest")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_fbref_time(n_leagues: int, n_seasons: int) -> str:
    """Human-readable ETA for FBRef downloads (10s/league-season + jitter)."""
    seconds = n_leagues * n_seasons * 12  # ~12s average with jitter
    if seconds < 60:
        return f"~{seconds}s"
    minutes = seconds // 60
    remaining = seconds % 60
    return f"~{minutes}m {remaining}s"


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
            # Understat only for Tier 1
            league_cfg = tiers_cfg["leagues"].get(slug, {})
            if league_cfg.get("tier") == "tier_1":
                try:
                    u_records = understat.fetch_league_stats(slug, season)
                    print(f"  {slug} (Understat): {len(u_records)} players")
                except Exception as exc:
                    print(f"  {slug} (Understat): FAILED -- {exc}")
        return None

    _print_section(f"Ingesting {season}")
    leagues_display = ", ".join(target_slugs[:5])
    if len(target_slugs) > 5:
        leagues_display += "..."
    print(f"  Leagues: {len(target_slugs)} ({leagues_display})")
    print(f"  Estimated FBRef time: {_estimate_fbref_time(len(target_slugs), 1)}")
    print(f"  Snapshot date: {snapshot_date.isoformat()}")

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
    print(f"\n  Completed in {elapsed:.0f}s ({elapsed / 60:.1f} min)")

    _print_summary(report)
    return report


# ---------------------------------------------------------------------------
# StatsBomb event sync
# ---------------------------------------------------------------------------

def sync_statsbomb_events(db, max_competitions: int | None = None) -> dict:
    """Sync StatsBomb open-data events (shot/pass coordinates).

    This is a separate step from the stat-snapshot pipeline because StatsBomb
    data lives in a different table (match_events) and has a different
    ingestion flow (competition -> match -> events).
    """
    from app.sources.statsbomb import StatsBombOpenDataSource

    _print_section("StatsBomb Event Sync")
    source = StatsBombOpenDataSource()

    try:
        competitions = source.fetch_competitions()
    except Exception as exc:
        logger.error("Failed to fetch StatsBomb competitions: %s", exc)
        return {"error": str(exc)}

    # Group by competition to show what's available
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
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ingest_real_data",
        description="Download real football data and seed the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --season 2025-26
  %(prog)s --season 2025-26 --leagues premier-league,la-liga
  %(prog)s --seasons 2023-24,2024-25,2025-26
  %(prog)s --season 2025-26 --dry-run
  %(prog)s --season 2025-26 --statsbomb
  %(prog)s --statsbomb-only --max-competitions 5
        """,
    )
    parser.add_argument(
        "--season",
        default=None,
        help="Single season to fetch (e.g. 2025-26). Default: current season.",
    )
    parser.add_argument(
        "--seasons",
        default=None,
        help="Comma-separated seasons to fetch (e.g. 2023-24,2024-25,2025-26).",
    )
    parser.add_argument(
        "--leagues",
        default=None,
        help="Comma-separated league slugs (default: all leagues in tiers.json).",
    )
    parser.add_argument(
        "--statsbomb",
        action="store_true",
        help="Also sync StatsBomb open event data (slower -- match-by-match).",
    )
    parser.add_argument(
        "--statsbomb-only",
        action="store_true",
        help="Only sync StatsBomb events (skip FBRef/Understat stat snapshots).",
    )
    parser.add_argument(
        "--max-competitions",
        type=int,
        default=None,
        help="Max StatsBomb competitions to sync (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print data without writing to the database.",
    )
    parser.add_argument(
        "--require-tier-completeness",
        action="store_true",
        help="Withhold a tier's percentiles until every league in it is ingested.",
    )
    parser.add_argument(
        "--dataset-mode",
        choices=["fixture-demo", "production"],
        default=None,
        help="Override STATLAS_DATASET_MODE (set to 'production' after first real scrape).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Dataset mode override
    if args.dataset_mode:
        os.environ["STATLAS_DATASET_MODE"] = args.dataset_mode

    # Resolve seasons
    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",")]
    elif args.season:
        seasons = [args.season]
    else:
        from app.config import CURRENT_SEASON
        seasons = [CURRENT_SEASON]

    # Resolve league slugs
    league_slugs = None
    if args.leagues:
        league_slugs = [s.strip() for s in args.leagues.split(",")]

    # Print plan
    _print_section("Statlas Real-Data Ingestion")
    print(f"  Seasons: {', '.join(seasons)}")
    if league_slugs:
        print(f"  Leagues: {', '.join(league_slugs)}")
    else:
        tiers = load_tiers()
        print(f"  Leagues: all ({len(tiers['leagues'])} leagues across 3 tiers)")
    sb_label = "yes" if args.statsbomb or args.statsbomb_only else "no"
    print(f"  StatsBomb events: {sb_label}")
    dr_label = "yes" if args.dry_run else "no"
    print(f"  Dry run: {dr_label}")
    db_url = get_settings().database_url or "SQLite (data/dev.db)"
    print(f"  Database: {db_url}")
    if get_settings().dataset_mode == "fixture-demo" and not args.dry_run:
        print()
        print("  WARN Dataset mode is 'fixture-demo'. After the first real scrape, run with:")
        print("    STATLAS_DATASET_MODE=production python scripts/ingest_real_data.py ...")

    # Setup database
    if not args.dry_run:
        create_schema()

    # StatsBomb-only mode
    if args.statsbomb_only:
        if args.dry_run:
            print("\n  --dry-run is not supported for --statsbomb-only mode")
            return 1
        with session_scope() as db:
            sync_statsbomb_events(db, max_competitions=args.max_competitions)
        return 0

    # Main ingestion loop
    all_reports = []
    for season in seasons:
        if args.dry_run:
            with session_scope() as db:
                ingest_season(
                    db,
                    season,
                    league_slugs=league_slugs,
                    do_statsbomb=False,
                    dry_run=True,
                )
        else:
            with session_scope() as db:
                report = ingest_season(
                    db,
                    season,
                    league_slugs=league_slugs,
                    do_statsbomb=args.statsbomb,
                    require_tier_completeness=args.require_tier_completeness,
                )
                if report:
                    all_reports.append((season, report))

    # StatsBomb event sync (after all stat snapshots)
    if args.statsbomb and not args.dry_run:
        with session_scope() as db:
            sync_statsbomb_events(db, max_competitions=args.max_competitions)

    # Final summary for multi-season runs
    if len(all_reports) > 1:
        _print_section("Multi-Season Summary")
        total_snaps = 0
        total_pubs = 0
        total_errors = 0
        for season, report in all_reports:
            total_snaps += report.snapshots_inserted
            total_pubs += report.published_rows
            total_errors += len(report.errors)
            status = "OK" if not report.errors else "WARN"
            print(f"  {status} {season}: {report.snapshots_inserted} snapshots, {report.published_rows} published, {len(report.errors)} errors")
        print(f"\n  Total: {total_snaps} snapshots, {total_pubs} published, {total_errors} errors")

    # Hint about dataset mode
    if not args.dry_run and get_settings().dataset_mode == "fixture-demo":
        print(f"\n{'=' * 60}")
        print("  NEXT STEP: Switch to production dataset mode")
        print(f"  {'-' * 58}")
        print("  export STATLAS_DATASET_MODE=production")
        print("  # Then restart the API server to serve real data")
        print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
