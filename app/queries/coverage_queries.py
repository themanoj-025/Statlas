"""Coverage queries — the honest gating mechanism for the UI.

Constitution §3 + Never-List #8: a screen may only claim coverage the matrix
contains. The UI calls these functions before rendering shot maps, per-league
tables, or any coverage-dependent feature.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import DataCoverage


def get_data_coverage(db: Session, league_id: int | None = None) -> list[dict[str, Any]]:
    """Coverage rows, optionally filtered by league. Each row states source,
    identifier, seasons, last successful scrape, and status."""
    query = db.query(DataCoverage).order_by(DataCoverage.source, DataCoverage.source_identifier)
    if league_id is not None:
        query = query.filter(DataCoverage.league_id == league_id)
    return [
        {
            "league_id": row.league_id,
            "source": row.source,
            "source_identifier": row.source_identifier,
            "seasons_available": row.seasons_available or [],
            "last_successful_scrape": row.last_successful_scrape,
            "status": row.status,
        }
        for row in query.all()
    ]


def has_source_coverage(
    db: Session,
    *,
    source: str,
    source_identifier: str,
    season: str | None = None,
    require_active: bool = True,
) -> bool:
    """True only when the coverage matrix actually contains the claim —
    the single check the shot-map/event-data UI must pass before rendering."""
    row = (
        db.query(DataCoverage)
        .filter_by(source=source, source_identifier=source_identifier)
        .first()
    )
    if row is None:
        return False
    if require_active and row.status != "active":
        return False
    # SIM103: express the final gate as a direct boolean.
    return season is None or season in (row.seasons_available or [])
