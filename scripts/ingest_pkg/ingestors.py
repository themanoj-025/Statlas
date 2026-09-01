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
        for lg in all_leagues
        if tracker.is_completed(s, lg)
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
            except (requests.RequestException, ValueError, KeyError, OSError) as exc:
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
        ingest_season(
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
