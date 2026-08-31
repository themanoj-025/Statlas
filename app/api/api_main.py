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

from app.api.analytics_views import router as analytics_router
from app.api.archetype_views import router as archetype_router
from app.api.assistant_views import router as assistant_router
from app.api.billing_views import router as billing_router
from app.api.comment_views import router as comment_router
from app.api.dashboard_views import router as dashboard_router
from app.api.e2e_views import router as e2e_router
from app.api.helpers import _log_player_view, _with_session
from app.api.middleware import (
    body_size_limit_middleware,
    csrf_middleware,
    security_and_rate_limit_middleware,
)
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

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
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

# --- OpenTelemetry distributed tracing (OTEL_ENABLED=true) ---
try:
    from app.tracing import setup_tracing
    _otel_ok = setup_tracing("statlas-api")
    if _otel_ok:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass


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
async def value_error_handler(_, exc: ValueError) -> Any:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "validation_error", "message": str(exc)}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
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
