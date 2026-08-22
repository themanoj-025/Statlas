"""Statlas pipeline CLI.

Examples:
    python cli.py weekly-refresh --season 2025-26
    python cli.py scrape fbref --league premier-league --season 2025-26 --dry-run
    python cli.py reconcile-list
    python cli.py reconcile-resolve --queue-id 3 --player-id 12 --note "confirmed by agent X"
    python cli.py anomalies-list
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from app.db import create_schema, session_scope
from app.models import IngestionAnomaly

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="statlas", description="Statlas data pipeline"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- ingest (real data download) ----------------------------------------
    ingest = sub.add_parser(
        "ingest", help="download real data from free sources and seed the DB"
    )
    ingest.add_argument(
        "--season", default=None, help="single season (e.g. 2025-26)"
    )
    ingest.add_argument(
        "--seasons", default=None, help="comma-separated seasons (e.g. 2023-24,2024-25)"
    )
    ingest.add_argument(
        "--leagues", default=None, help="comma-separated league slugs"
    )
    ingest.add_argument(
        "--statsbomb", action="store_true", help="also sync StatsBomb events"
    )
    ingest.add_argument(
        "--dry-run", action="store_true", help="fetch without writing to DB"
    )
    ingest.add_argument(
        "--dataset-mode",
        choices=["fixture-demo", "production"],
        default=None,
        help="override dataset mode (set 'production' after first real scrape)",
    )
    ingest.add_argument(
        "-v", "--verbose", action="store_true", help="debug logging"
    )

    weekly = sub.add_parser("weekly-refresh", help="run the full weekly refresh")
    weekly.add_argument("--season", required=True)
    weekly.add_argument(
        "--date", default=None, help="ISO snapshot date (defaults to now)"
    )
    weekly.add_argument("--leagues", default=None, help="comma-separated league slugs")
    weekly.add_argument(
        "--statsbomb", action="store_true", help="also sync StatsBomb competitions"
    )
    weekly.add_argument(
        "--fixtures", action="store_true", help="also sync API-Football fixtures"
    )
    weekly.add_argument(
        "--require-tier-completeness",
        action="store_true",
        help="withhold a tier's percentiles until EVERY league in it is ingested "
        "for the season (§1.4 gate; coverage matrix as arbiter). Defaults ON in "
        "production dataset mode.",
    )

    scrape = sub.add_parser(
        "scrape", help="scrape one source and print the resulting records"
    )
    scrape.add_argument("source", choices=["fbref", "understat"])
    scrape.add_argument("--league", required=True)
    scrape.add_argument("--season", required=True)
    scrape.add_argument(
        "--dry-run", action="store_true", help="print records without writing to DB"
    )

    sub.add_parser("reconcile-list", help="list pending reconciliation items")
    resolve = sub.add_parser(
        "reconcile-resolve", help="manually resolve a queue item to a player"
    )
    resolve.add_argument("--queue-id", type=int, required=True)
    resolve.add_argument("--player-id", type=int, required=True)
    resolve.add_argument("--note", default=None)

    anomalies = sub.add_parser("anomalies-list", help="list unresolved anomalies")
    anomalies.add_argument("--all", action="store_true", help="also show resolved")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.command == "ingest":
        # Delegate to the comprehensive ingestion script's logic
        import os as _os

        if args.verbose:
            _os.environ["STATLAS_LOG_LEVEL"] = "DEBUG"
        if args.dataset_mode:
            _os.environ["STATLAS_DATASET_MODE"] = args.dataset_mode

        # Build sys.argv for the ingestion script
        ingest_args = []
        if args.season:
            ingest_args += ["--season", args.season]
        if args.seasons:
            ingest_args += ["--seasons", args.seasons]
        if args.leagues:
            ingest_args += ["--leagues", args.leagues]
        if args.statsbomb:
            ingest_args.append("--statsbomb")
        if args.dry_run:
            ingest_args.append("--dry-run")
        if args.verbose:
            ingest_args.append("-v")

        # Run the ingestion script's main() with patched argv
        old_argv = sys.argv
        try:
            sys.argv = ["statlas ingest"] + ingest_args
            from scripts.ingest_real_data import main as ingest_main

            return ingest_main()
        finally:
            sys.argv = old_argv

    if args.command == "weekly-refresh":
        from app.orchestration.weekly_refresh import run_weekly_refresh
        from app.sources.api_football import APIFootballSource
        from app.sources.fbref import FBrefSource
        from app.sources.statsbomb import StatsBombOpenDataSource
        from app.sources.understat import UnderstatSource

        create_schema()
        snapshot_date = (
            datetime.fromisoformat(args.date)
            if args.date
            else datetime.now(timezone.utc)
        )
        league_slugs = args.leagues.split(",") if args.leagues else None
        from app.config import get_settings

        # §1.4 tier-completeness gate: production runs withhold a tier until
        # every league in it is ingested; the flag explicitly overrides (or
        # the fixture-demo mode keeps the single-league test contract).
        gate = (
            args.require_tier_completeness
            or get_settings().dataset_mode == "production"
        )
        with session_scope() as db:
            report = run_weekly_refresh(
                db,
                args.season,
                snapshot_date=snapshot_date,
                league_slugs=league_slugs,
                fbref_source=FBrefSource(),
                understat_source=UnderstatSource(),
                statsbomb_source=StatsBombOpenDataSource(),
                api_football_source=APIFootballSource(),
                do_statsbomb=args.statsbomb,
                do_fixtures=args.fixtures,
                require_tier_completeness=gate,
            )
        print(report)
        return 0

    if args.command == "scrape":
        from app.sources.fbref import FBrefSource
        from app.sources.understat import UnderstatSource

        source = FBrefSource() if args.source == "fbref" else UnderstatSource()
        records = source.fetch_league_stats(args.league, args.season)
        if args.dry_run:
            for r in records[:20]:
                print(
                    r.source, r.player_name, r.team_name, r.minutes_played, r.raw_stats
                )
            print(f"... {len(records)} records total (dry run, nothing written)")
            return 0
        from app.reconciliation import Reconciler

        create_schema()
        with session_scope() as db:
            from dataclasses import dataclass
            from dataclasses import field as dc_field

            from app.orchestration.weekly_refresh import ingest_source_records

            @dataclass
            class _MiniReport:
                records_ingested: int = 0
                snapshots_inserted: int = 0
                snapshots_existing: int = 0
                records_unmatched: int = 0
                errors: list = dc_field(default_factory=list)

                def add(self, **kw):
                    for k, v in kw.items():
                        if hasattr(self, k):
                            setattr(self, k, getattr(self, k) + v)

            report = _MiniReport()
            reconciler = Reconciler(db)
            ingest_source_records(
                db,
                records,
                snapshot_date=datetime.now(timezone.utc),
                reconciler=reconciler,
                report=report,
            )
            print(report)
        return 0

    if args.command == "reconcile-list":
        from app.reconciliation import list_pending

        create_schema()
        with session_scope() as db:
            for item in list_pending(db):
                print(
                    item.id,
                    item.source,
                    item.source_name,
                    "|",
                    item.source_team,
                    "|",
                    item.status,
                )
        return 0

    if args.command == "reconcile-resolve":
        from app.reconciliation import resolve_queue_item

        create_schema()
        with session_scope() as db:
            item = resolve_queue_item(db, args.queue_id, args.player_id, note=args.note)
            print(f"resolved {item.id}: {item.source_name} -> player {args.player_id}")
        return 0

    if args.command == "anomalies-list":
        create_schema()
        with session_scope() as db:
            query = db.query(IngestionAnomaly).order_by(
                IngestionAnomaly.flagged_at.desc()
            )
            if not args.all:
                query = query.filter(IngestionAnomaly.resolved.is_(False))
            for anomaly in query.limit(100).all():
                status = "UNRESOLVED" if not anomaly.resolved else "resolved"
                print(
                    anomaly.id,
                    status,
                    anomaly.field_name,
                    anomaly.raw_value,
                    anomaly.expected_range,
                )
        return 0

    return 2


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    sys.exit(main())
