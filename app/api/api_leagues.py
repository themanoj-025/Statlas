"""Statlas API — league endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app.models import League

# Leagues
# ---------------------------------------------------------------------------


@app.get("/api/v1/leagues", response_model=list[LeagueEntry])
def leagues() -> list[dict[str, Any]]:
    from app.cache import get_cache
    from app.queries.league_queries import get_league_catalog

    cache = get_cache()
    cached = cache.get("api:leagues")
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass
    result = _with_session(get_league_catalog)
    with suppress(Exception):
        cache.set("api:leagues", _json.dumps(result, default=str), ttl=300)
    return result


@app.get("/api/v1/leagues/{league_slug}")
def league_detail(league_slug: str) -> dict[str, Any]:
    from app.queries.league_queries import get_league_detail

    detail = _with_session(get_league_detail, league_slug)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"unknown league '{league_slug}'")
    return detail


@app.get("/api/v1/leagues/{league_slug}/hub")
def league_hub(league_slug: str, season: str | None = None) -> dict[str, Any]:
    from app.queries.league_page_queries import get_league_hub_data

    hub = _with_session(get_league_hub_data, league_slug, season=season)
    if hub is None:
        raise HTTPException(status_code=404, detail=f"unknown league '{league_slug}'")
    return hub


@app.get("/api/v1/leagues/{league_slug}/stats")
def league_stats(
    league_slug: str,
    metric -> None:
    season: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any] -> None:
    from app.queries.league_queries import get_league_stats_table

    return _with_session(
        get_league_stats_table, league_slug, metric=metric, season=season, limit=limit
    )


# ---------------------------------------------------------------------------
