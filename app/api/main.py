"""Statlas API — /api/v1 (versioned from day one, Constitution §4).

This is the ONLY data-access layer the frontend talks to. It wraps the
Phase 1/2 internal query functions (queries/*) — the Next.js server-rendered
pages and client components never touch SQLAlchemy directly.

Honesty by construction:
- Only PUBLISHED percentile rows are served (the anomaly gate is enforced by
  the query layer, never bypassed here).
- The dataset mode is reported by /meta and rendered as a visible banner by
  the frontend until a real pipeline run + STATLAS_DATASET_MODE=production.
- Coverage-dependent features (shot-map teasers) are gated on the coverage
  matrix via queries/coverage_queries.
"""

from __future__ import annotations

import json as _json
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from app.api.analytics_views import router as analytics_router
from app.api.archetype_views import router as archetype_router
from app.api.assistant_views import router as assistant_router
from app.api.billing_views import router as billing_router
from app.api.comment_views import router as comment_router
from app.api.dashboard_views import router as dashboard_router
from app.api.e2e_views import router as e2e_router
from app.api.org_views import router as org_router
from app.api.public_views import router as public_api_router
from app.api.registry_view import public_meta
from app.api.report_views import router as report_router
from app.api.schemas import (
    CoverageResponse,
    HealthResponse,
    LeaderboardResponse,
    LeagueEntry,
    MetaResponse,
    PlayerProfileResponse,
    PlayerSearchResult,
    PositionEntry,
    SimilarPlayerEntry,
    TrendResponse,
)
from app.api.search_views import router as search_router
from app.api.tactical_views import router as tactical_router
from app.api.transfer_views import router as transfer_router
from app.api.watch_views import router as watch_router
from app.api.workspace_views import router as workspace_router
from app.config import CURRENT_SEASON, get_settings, load_registry
from app.db import session_scope
from app.logging_setup import new_request_id

from app.api.helpers import _log_player_view, _with_session
from app.api.middleware import (
    CSRF_EXEMPT_PATHS,
    body_size_limit_middleware,
    csrf_middleware,
    security_and_rate_limit_middleware,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — configure logging on startup."""
    from app.logging_setup import setup_logging

    setup_logging(level=_settings.log_level)
    yield


app = FastAPI(
    title="Statlas API",
    version="1.0.0",
    description="Versioned internal API for the Statlas frontend.\n\n"
    "Sports analytics platform with player stats, tactical analysis, and AI assistant.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "health",
            "description": "Service health check endpoints",
        },
        {
            "name": "billing",
            "description": "Subscription and billing management",
        },
        {
            "name": "players",
            "description": "Player data and statistics",
        },
        {
            "name": "tactical",
            "description": "Tactical analysis and formations",
        },
        {
            "name": "search",
            "description": "Player and team search",
        },
        {
            "name": "reports",
            "description": "Report generation and export",
        },
        {
            "name": "assistant",
            "description": "AI-powered sports analysis assistant",
        },
        {
            "name": "workspace",
            "description": "User workspace and saved analyses",
        },
    ],
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    # Phase 4: auth uses cookie sessions, so credentialed requests are allowed
    # from the web app origin (billing POST routes included).
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    max_age=86400,  # Cache preflight for 24 hours
)
# GZip compression for all responses (reduces payload size ~70%)app.add_middleware(GZipMiddleware, minimum_size=500)

# Register extracted middleware (order matters: outermost runs first)
app.middleware("http")(body_size_limit_middleware)
app.middleware("http")(csrf_middleware)
app.middleware("http")(security_and_rate_limit_middleware)

app.include_router(billing_router)
app.include_router(e2e_router)
app.include_router(assistant_router)
app.include_router(public_api_router)
app.include_router(workspace_router)
app.include_router(search_router)
app.include_router(report_router)
app.include_router(watch_router)
app.include_router(dashboard_router)
app.include_router(archetype_router)
app.include_router(transfer_router)
app.include_router(tactical_router)
app.include_router(org_router)
app.include_router(comment_router)
app.include_router(analytics_router)


VALID_POSITIONS = {"GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"}


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "validation_error", "message": str(exc)}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardized error envelope for all HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": exc.detail,
            }
        },
    )


# ---------------------------------------------------------------------------
# Meta / health
# ---------------------------------------------------------------------------


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    """Health check that verifies database and Redis connectivity."""
    settings = get_settings()
    db_status = "healthy"
    redis_status = "healthy"
    try:
        from sqlalchemy import text

        with session_scope() as db:
            db.execute(text("SELECT 1"))
    except (OSError, RuntimeError) as exc:
        db_status = f"unhealthy: {exc}"
    try:
        from app.cache import get_cache

        cache = get_cache()
        if hasattr(cache, 'redis'):
            cache.redis.ping()
    except (OSError, ConnectionError) as exc:
        redis_status = f"unhealthy: {exc}"

    overall = "ok" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "api_version": "1.0.0",
        "dataset_mode": settings.dataset_mode,
    }


@app.get("/api/v1/readiness")
def readiness() -> dict[str, Any]:
    """Readiness check — returns 503 if not ready to serve traffic."""
    try:
        from sqlalchemy import text

        with session_scope() as db:
            db.execute(text("SELECT 1"))
        return {"ready": True}
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.get("/api/v1/meta", response_model=MetaResponse)
def meta() -> dict[str, Any]:
    from app.cache import get_cache

    cache = get_cache()
    cached = cache.get("api:meta")
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    settings = get_settings()
    registry = load_registry()
    result = {
        **public_meta(),
        "dataset": {
            "mode": settings.dataset_mode,
            "note": settings.dataset_note,
        },
        "weekly_refresh_cadence": "Every Wednesday 03:00 UTC",
        "index_definition": (
            f"{registry['index_metric_id']} — weighted average of percentile "
            "ranks within season × position group × league tier"
        ),
    }
    try:
        cache.set("api:meta", _json.dumps(result, default=str), ttl=300)
    except (OSError, ConnectionError, TypeError):
        pass  # caching failure must never break the response
    return result


# ---------------------------------------------------------------------------
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
    metric: str = Query("si_gls_p90"),
    season: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    from app.queries.league_queries import get_league_stats_table

    return _with_session(
        get_league_stats_table, league_slug, metric=metric, season=season, limit=limit
    )


# ---------------------------------------------------------------------------
# Leaderboards
# ---------------------------------------------------------------------------


@app.get("/api/v1/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    metric: str = Query("si_index"),
    season: str = CURRENT_SEASON,
    league: str | None = Query(
        None, description="league slug (omitting = whole tier/all)"
    ),
    tier: str | None = Query(None, description="tier_1|tier_2|tier_3"),
    position: str | None = Query(None, description="GK|CB|FB|DM|CM|AM|W|ST"),
    min_minutes: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    sort_by: str = Query("value"),
    sort_dir: str | None = Query(None),
) -> dict[str, Any]:
    from app.cache import get_cache
    from app.queries.leaderboard_queries import get_leaderboard_filtered

    if position is not None and position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400, detail=f"unknown position group '{position}'"
        )
    if tier is not None and tier not in {"tier_1", "tier_2", "tier_3"}:
        raise HTTPException(status_code=400, detail=f"unknown tier '{tier}'")
    if sort_by not in {"value", "minutes", "name", "club"}:
        raise HTTPException(status_code=400, detail=f"unknown sort_by '{sort_by}'")
    if sort_dir is not None and sort_dir.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail=f"sort_dir must be 'asc' or 'desc', got '{sort_dir}'")

    # Cache key: includes all query params that affect the result.
    # TTL 300s (5 min) — data refreshes weekly, short TTL keeps responses
    # fresh during rapid navigation while eliminating redundant DB hits.
    cache = get_cache()
    cache_key = (
        f"api:lb:{metric}:{season}:{league or '_'}:{tier or '_'}:"
        f"{position or '_'}:{min_minutes or '_'}:{page}:{limit}:"
        f"{sort_by}:{sort_dir or '_'}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        result = get_leaderboard_filtered(
            db,
            metric=metric,
            season=season,
            league_slugs=[league] if league else None,
            tier=tier,
            position_group=position,
            min_minutes=min_minutes,
            limit=limit,
            offset=(page - 1) * limit,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), 300)
    return result


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/search", response_model=list[PlayerSearchResult])
def player_search(
    q: str = Query(..., min_length=1, max_length=64), limit: int = Query(8, ge=1, le=25)
) -> list[dict[str, Any]]:
    from app.queries.player_queries import search_players

    return _with_session(search_players, q, limit=limit)


@app.get("/api/v1/players/by-slug/{slug}", response_model=PlayerProfileResponse)
def player_by_slug(slug: str, request: Request) -> dict[str, Any]:
    from app.api.player_view import build_player_payload
    from app.cache import get_cache
    from app.queries.player_queries import resolve_player_slug

    # Cache: player profiles are read-heavy, change only on weekly refresh.
    # TTL 300s (5 min). Activity logging runs regardless of cache hit.
    cache = get_cache()
    cache_key = f"api:player:{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            payload = _json.loads(cached)
            # Activity logging still runs on cache hit (best-effort)
            _log_player_view(request, payload["player"]["player_id"])
            return payload
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        resolved = resolve_player_slug(db, slug)
        if resolved is None:
            raise HTTPException(
                status_code=404, detail=f"no player matches slug '{slug}'"
            )
        payload = build_player_payload(db, resolved["player_id"])
        if payload is None:
            raise HTTPException(status_code=404, detail="player has no profile data")
        payload["player"]["canonical_slug"] = resolved["canonical_slug"]
        payload["player"]["is_canonical"] = resolved["canonical"]

        # Phase 13: log view activity (deduplicated, best-effort)
        _log_player_view(request, resolved["player_id"])

    with suppress(Exception):
        cache.set(cache_key, _json.dumps(payload, default=str), 300)
    return payload


@app.get("/api/v1/players/{player_id}/similar", response_model=list[SimilarPlayerEntry])
def player_similar(player_id: int, limit: int = Query(5, ge=1, le=10)) -> list[dict[str, Any]]:
    from app.cache import get_cache
    from app.queries.player_queries import get_player_profile
    from app.queries.similar_players import get_similar_players

    # Cache: similar players depend on percentile data (weekly refresh).
    # TTL 300s (5 min) — same rationale as leaderboard.
    cache = get_cache()
    cache_key = f"api:similar:{player_id}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            return _json.loads(cached)
        except (ValueError, TypeError, _json.JSONDecodeError):
            pass

    with session_scope() as db:
        if get_player_profile(db, player_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown player {player_id}")
        result = get_similar_players(db, player_id, limit=limit)
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), 300)
    return result


# ---------------------------------------------------------------------------
# Phase 3 — trend / time-series (Part A)
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/{player_id}/trend", response_model=TrendResponse)
def player_trend(
    player_id: int,
    metric: str = Query(...),
    window: int = Query(5, ge=1, le=50),
) -> dict[str, Any]:
    from app.queries.trend_queries import get_player_trend

    with session_scope() as db:
        trend = get_player_trend(db, player_id, metric, window=window)
        if trend is None:
            raise HTTPException(status_code=404, detail=f"unknown player {player_id}")
        return trend


# ---------------------------------------------------------------------------
# Phase 3 — shot / pass maps (Part B, coverage-gated)
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/{player_id}/events")
def player_event_coverage(player_id: int) -> dict[str, Any]:
    from app.queries.event_queries import get_player_event_coverage

    return _with_session(get_player_event_coverage, player_id)


@app.get("/api/v1/players/{player_id}/events/matches")
def player_event_matches(
    player_id: int,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_event_matches

    return _with_session(
        get_player_event_matches, player_id, competition_id=competition, season=season
    )


@app.get("/api/v1/players/{player_id}/events/shots")
def player_event_shots(
    player_id: int,
    match: str | None = None,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_events

    return _with_session(
        get_player_events,
        player_id,
        event_type="Shot",
        match_id=match,
        competition_id=competition,
        season=season,
    )


@app.get("/api/v1/players/{player_id}/events/passes")
def player_event_passes(
    player_id: int,
    match: str | None = None,
    competition: str | None = None,
    season: str | None = None,
) -> list[dict[str, Any]]:
    from app.queries.event_queries import get_player_events

    return _with_session(
        get_player_events,
        player_id,
        event_type="Pass",
        match_id=match,
        competition_id=competition,
        season=season,
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@app.get("/api/v1/clubs/{league_slug}/{team_slug}")
def team_profile(league_slug: str, team_slug: str, season: str | None = None) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Coverage / methodology / positions
# ---------------------------------------------------------------------------


@app.get("/api/v1/coverage", response_model=CoverageResponse)
def coverage(league_id: int | None = None) -> dict[str, Any]:
    from app.queries.coverage_queries import get_data_coverage
    from app.queries.event_queries import get_statsbomb_competitions

    with session_scope() as db:
        rows = get_data_coverage(db, league_id=league_id)
        return {
            "rows": rows,
            "statsbomb_competitions": get_statsbomb_competitions(db),
            "attribution": {
                "statsbomb": "Data by StatsBomb — open data (StatsBomb Public Data User Agreement; research use with attribution). Shot and pass maps render only for competitions in StatsBomb Open Data coverage.",
                "fbref": "Per-90 statistics from FBref (Sports Reference). Published as derived, normalized metrics only.",
                "understat": "xG/xA for the Big-5 from Understat (Tier 1 model).",
            },
            "generated": datetime.now(timezone.utc)
            .date()
            .isoformat(),  # UTC policy (timezone-policy.md)
        }


@app.get("/api/v1/positions", response_model=list[PositionEntry])
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
            db, metric=meta["index_metric_id"], season=CURRENT_SEASON,
        )
        out = []
        for group in meta["position_groups"]:
            out.append({**group, "qualifying_counts": counts_by_group.get(group["code"], {})})
        result = out
    with suppress(Exception):
        cache.set(cache_key, _json.dumps(result, default=str), ttl=300)
    return result


@app.get("/api/v1/methodology")
def methodology() -> dict[str, Any]:
    return public_meta()


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint (Phase 19 — observability)
# ---------------------------------------------------------------------------


@app.get("/metrics")
def metrics() -> Any:
    """Prometheus-format metrics for production monitoring.

    Exposes request counts, durations (histogram), error counts, cache stats,
    and uptime. Designed to be scraped by Prometheus without any external
    dependencies (no prometheus_client library required).
    """
    from fastapi.responses import PlainTextResponse

    from app.metrics import get_metrics_collector

    return PlainTextResponse(
        content=get_metrics_collector().render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
