"""Statlas API — team, coverage, and meta endpoints."""

from __future__ import annotations

import json as _json
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.api.registry_view import public_meta
from app.api.schemas import CoverageResponse, PositionEntry
from app.config import CURRENT_SEASON
from app.db import session_scope

router = APIRouter(tags=["teams"])


@router.get("/api/v1/clubs/{league_slug}/{team_slug}")
def team_profile(
    league_slug: str, team_slug: str, season: str | None = None
) -> dict[str, Any]:
    from app.queries.team_queries import get_team_profile

    with session_scope() as db:
        payload = get_team_profile(
            db, league_slug=league_slug, team_slug=team_slug, season=season
        )
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"no team '{team_slug}' in league '{league_slug}'",
            )
        return payload


@router.get("/api/v1/coverage", response_model=CoverageResponse)
def coverage(league_id: int | None = None) -> dict[str, Any]:
    from app.queries.coverage_queries import get_data_coverage
    from app.queries.event_queries import get_statsbomb_competitions

    with session_scope() as db:
        rows = get_data_coverage(db, league_id=league_id)
        return {
            "rows": rows,
            "statsbomb_competitions": get_statsbomb_competitions(db),
            "attribution": {
                "statsbomb": (
                    "Data by StatsBomb — open data (StatsBomb Public Data User Agreement; "
                    "research use with attribution). Shot and pass maps render only for "
                    "competitions in StatsBomb Open Data coverage."
                ),
                "fbref": (
                    "Per-90 statistics from FBref (Sports Reference). "
                    "Published as derived, normalized metrics only."
                ),
                "understat": "xG/xA for the Big-5 from Understat (Tier 1 model).",
            },
            "generated": datetime.now(timezone.utc).date().isoformat(),
        }


@router.get("/api/v1/positions", response_model=list[PositionEntry])
def positions() -> list[dict[str, Any]]:
    from app.cache import get_cache

    meta = public_meta()
    from app.queries.leaderboard_queries import get_qualifying_counts

    cache = get_cache()
    cache_key = f"api:positions:{CURRENT_SEASON}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        counts_by_group = get_qualifying_counts(
            db,
            metric=meta["index_metric_id"],
            season=CURRENT_SEASON,
        )
        out = []
        for group in meta["position_groups"]:
            out.append(
                {**group, "qualifying_counts": counts_by_group.get(group["code"], {})}
            )
        result = out
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), ttl=300)
    return result


@router.get("/api/v1/methodology")
def methodology() -> dict[str, Any]:
    return public_meta()


@router.get("/metrics")
def metrics() -> Any:
    """Prometheus-format metrics for production monitoring."""
    from app.metrics import get_metrics_collector

    return PlainTextResponse(
        content=get_metrics_collector().render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
