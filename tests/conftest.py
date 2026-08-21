"""Shared test fixtures.

The database is an in-memory SQLite built from the ORM models — the same
models that mirror schema.sql — so tests exercise the real query/code paths
without needing PostgreSQL. The suite always runs on SQLite (locally AND in
CI — see .github/workflows/ci.yml); PostgreSQL is exercised through schema.sql
parity (native_enum=False keeps the two interchangeable).
"""

from __future__ import annotations

import os

os.environ.setdefault("STATLAS_ENV", "test")

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import load_registry
from app.models import Base, League

FIXTURES_DIR = Path(__file__).parent / "fixtures"

SNAPSHOT_DATE = datetime(2026, 8, 12, 3, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def premier_league(db) -> League:
    league = League(
        slug="premier-league",
        name="Premier League",
        country="England",
        tier="tier_1",
        external_ids={"fbref_comp": 9, "understat": "EPL", "api_football": 39},
    )
    db.add(league)
    db.commit()
    return league


@pytest.fixture()
def small_pool():
    """Tests compute percentiles with small synthetic pools; the registry's
    min_pool_size (30) and qualifying threshold are test-overridden. The loaded
    registry is a process-wide cached object, so the override applies to the
    pipeline code paths too."""
    registry = load_registry()
    original = (registry["min_pool_size"], registry["qualifying_minutes"])
    registry["min_pool_size"] = 5
    registry["qualifying_minutes"] = 900
    yield registry
    registry["min_pool_size"], registry["qualifying_minutes"] = original


def fixtures_dir() -> Path:
    return FIXTURES_DIR


def compute_and_publish(db, *, snapshot_date, season, **kwargs):
    """Compute percentile/index rows AND publish them — the pipeline's publish
    gate (run_weekly_refresh step 6). Tests that seed directly must go through
    this: the query layer serves PUBLISHED rows only (Constitution: nothing is
    queryable until anomaly checks passed and the run is marked published).
    """
    from datetime import datetime, timezone

    from app.compute.percentiles import compute_percentiles
    from app.orchestration.weekly_refresh import publish_run

    now = datetime.now(timezone.utc)
    report = compute_percentiles(
        db, snapshot_date=snapshot_date, season=season, now=now, **kwargs
    )
    publish_run(db, now)
    return report


@pytest.fixture(autouse=True)
def _ensure_clean_rate_limiter():
    """Reset the in-memory rate limiter before every test to prevent
    cross-test rate-limit exhaustion (e.g., multiple registrations from
    the same test IP)."""
    import app.config as _cfg

    # Ensure test environment is active (disables CSRF middleware)
    _cfg._settings = None  # reset cached Settings singleton

    from app.rate_limiting import get_rate_limiter

    limiter = get_rate_limiter()
    if hasattr(limiter, "reset_all"):
        limiter.reset_all()
    yield
