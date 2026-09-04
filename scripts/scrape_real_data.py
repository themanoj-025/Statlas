import logging
import os
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Set dataset mode to production so it's treated as real data
os.environ["STATLAS_DATASET_MODE"] = "production"
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{PROJECT_ROOT / 'data' / 'dev.db'}")

from app.config import load_tiers
from app.db import session_scope
from app.orchestration.weekly_refresh import run_weekly_refresh
from app.sources.fbref import FBrefSource
from app.sources.understat import UnderstatSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("real_scrape")

SEASON = "2025-26"
SNAPSHOT_DATE = datetime.now(timezone.utc)

def main() -> Any:
    # Initialize real sources
    fbref = FBrefSource()
    understat = UnderstatSource()

    # Get all configured leagues
    tiers_config = load_tiers()
    all_league_slugs = list(tiers_config["leagues"].keys())

    logger.info(f"Starting real scrape for {len(all_league_slugs)} leagues. This will take a while due to rate limits.")

    with session_scope() as db:
        # We don't require tier completeness here so that percentiles are computed even if it gets interrupted
        report = run_weekly_refresh(
            db=db,
            season=SEASON,
            snapshot_date=SNAPSHOT_DATE,
            league_slugs=all_league_slugs,
            fbref_source=fbref,
            understat_source=understat,
            statsbomb_source=None,  # skip events for speed
            api_football_source=None, # skip fixtures for speed
            require_tier_completeness=False
        )

        logger.info("=== Scrape Complete ===")
        logger.info(f"Leagues Scraped: {report.leagues_scraped}")
        logger.info(f"Records Ingested: {report.records_ingested}")
        logger.info(f"Snapshots Inserted: {report.snapshots_inserted}")
        logger.info(f"Percentile Rows: {report.percentile_rows}")

if __name__ == "__main__":
    main()
