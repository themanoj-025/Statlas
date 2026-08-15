"""Idempotency proof (Constitution: re-running a job does not duplicate rows).

Runs the full weekly refresh twice for the same snapshot date and asserts the
database is byte-identical in row counts: stat_snapshots are skipped by their
natural key, percentile rows by (stat_snapshot_id, metric_name), fixtures by
api_fixture_id, and coverage rows upsert.
"""
from __future__ import annotations

from app.models import DataCoverage, League, PercentileSnapshot, Player, StatSnapshot
from app.orchestration.weekly_refresh import run_weekly_refresh
from tests.conftest import SNAPSHOT_DATE
from tests.test_integration import (
    FakeFBrefSource,
    FakeUnderstatSource,
    _fixtures,
)

SEASON = "2025-26"


def _run(db, **kw):
    fbref, understat = _fixtures()
    return run_weekly_refresh(
        db,
        SEASON,
        snapshot_date=SNAPSHOT_DATE,
        league_slugs=["premier-league"],
        fbref_source=FakeFBrefSource(fbref),
        understat_source=FakeUnderstatSource(understat),
        **kw,
    )


def _state(db) -> dict:
    return {
        "leagues": db.query(League).count(),
        "players": db.query(Player).count(),
        "snapshots": db.query(StatSnapshot).count(),
        "percentiles": db.query(PercentileSnapshot).count(),
        "published": db.query(PercentileSnapshot).filter_by(is_published=True).count(),
        "coverage": db.query(DataCoverage).count(),
    }


def test_rerunning_weekly_refresh_does_not_duplicate_rows(db, small_pool):
    first = _run(db)
    state_after_first = _state(db)
    assert first.snapshots_inserted == 7

    second = _run(db)
    state_after_second = _state(db)

    assert state_after_second == state_after_first
    assert second.snapshots_inserted == 0
    assert second.snapshots_existing == 7
    assert second.percentile_rows == 0  # already computed for this snapshot


def test_coverage_upsert_does_not_duplicate(db, small_pool):
    _run(db)
    _run(db)
    coverage = db.query(DataCoverage).all()
    # uniqueness is per (source, source_identifier) — the schema's natural key.
    # fbref AND understat legitimately share the league slug as identifier.
    pairs = [(c.source, c.source_identifier) for c in coverage]
    assert len(pairs) == len(set(pairs))
    fbref_row = db.query(DataCoverage).filter_by(source="fbref", source_identifier="premier-league").one()
    assert fbref_row.seasons_available == [SEASON]
