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

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import auth
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
from app.api.search_views import router as search_router
from app.api.tactical_views import router as tactical_router
from app.api.transfer_views import router as transfer_router
from app.api.watch_views import router as watch_router
from app.api.workspace_views import router as workspace_router
from app.config import get_settings, load_registry
from app.db import session_scope

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Statlas API",
    version="1.0.0",
    description="Versioned internal API for the Statlas frontend (Phase 2).",
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


# --- Startup: configure structured logging ---
@app.on_event("startup")
def _setup_logging():
    from app.logging_setup import setup_logging

    setup_logging(level=_settings.log_level)


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    """1. Attach X-RateLimit-* headers to public-API responses (Part C1).
    2. Add security headers to every response.
    The public views set request.state.rate_limit during auth; this applies
    the headers on the way out."""
    import uuid

    # Generate request ID for tracing + structured logging
    from app.logging_setup import new_request_id

    req_id = new_request_id()
    request.state.request_id = req_id

    response = await call_next(request)

    # --- Rate limit headers ---
    try:
        from app.api.public_views import apply_rate_limit_headers

        apply_rate_limit_headers(response, request)
    except Exception:  # header decoration must never break a response
        pass

    # --- Security headers ---
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    # Content-Security-Policy
    csp_parts = [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self' https://api.resend.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    if _settings.csp_report_uri:
        csp_parts.append(f"report-uri {_settings.csp_report_uri}")
    response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

    return response


VALID_POSITIONS = {"GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"}


class ErrorDetail(BaseModel):
    detail: str


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _with_session(fn: Callable[[Any], Any], *args: Any, **kwargs: Any) -> Any:
    """Run a query function against a fresh session (closed on return)."""
    with session_scope() as db:
        return fn(db, *args, **kwargs)


# ---------------------------------------------------------------------------
# Meta / health
# ---------------------------------------------------------------------------


@app.get("/api/v1/health")
def health():
    """Health check that verifies database connectivity."""
    settings = get_settings()
    db_status = "healthy"
    try:
        from sqlalchemy import text

        with session_scope() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "api_version": "1.0.0",
        "dataset_mode": settings.dataset_mode,
    }


@app.get("/api/v1/readiness")
def readiness():
    """Readiness check — returns 503 if not ready to serve traffic."""
    try:
        from sqlalchemy import text

        with session_scope() as db:
            db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.get("/api/v1/meta")
def meta():
    settings = get_settings()
    registry = load_registry()
    return {
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


# ---------------------------------------------------------------------------
# Leagues
# ---------------------------------------------------------------------------


@app.get("/api/v1/leagues")
def leagues():
    from app.queries.league_queries import get_league_catalog

    return _with_session(get_league_catalog)


@app.get("/api/v1/leagues/{league_slug}")
def league_detail(league_slug: str):
    from app.queries.league_queries import get_league_detail

    detail = _with_session(get_league_detail, league_slug)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"unknown league '{league_slug}'")
    return detail


@app.get("/api/v1/leagues/{league_slug}/hub")
def league_hub(league_slug: str, season: str | None = None):
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
):
    from app.queries.league_queries import get_league_stats_table

    return _with_session(
        get_league_stats_table, league_slug, metric=metric, season=season, limit=limit
    )


# ---------------------------------------------------------------------------
# Leaderboards
# ---------------------------------------------------------------------------


@app.get("/api/v1/leaderboard")
def leaderboard(
    metric: str = Query("si_index"),
    season: str = "2025-26",
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
):
    from app.queries.leaderboard_queries import get_leaderboard_filtered

    if position is not None and position not in VALID_POSITIONS:
        raise HTTPException(
            status_code=400, detail=f"unknown position group '{position}'"
        )
    if tier is not None and tier not in {"tier_1", "tier_2", "tier_3"}:
        raise HTTPException(status_code=400, detail=f"unknown tier '{tier}'")
    if sort_by not in {"value", "minutes", "name", "club"}:
        raise HTTPException(status_code=400, detail=f"unknown sort_by '{sort_by}'")

    with session_scope() as db:
        return get_leaderboard_filtered(
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


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/search")
def player_search(
    q: str = Query(..., min_length=1, max_length=64), limit: int = Query(8, ge=1, le=25)
):
    from app.queries.player_queries import search_players

    return _with_session(search_players, q, limit=limit)


@app.get("/api/v1/players/by-slug/{slug}")
def player_by_slug(slug: str, request: Request):
    from app.activity import log_activity
    from app.api.player_view import build_player_payload
    from app.queries.player_queries import resolve_player_slug

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
        try:
            user = auth.user_from_session(
                db, request.cookies.get(get_settings().session_cookie_name)
            )
            if user is not None:
                log_activity(
                    db,
                    user_id=user.id,
                    entity_type="player",
                    entity_id=resolved["player_id"],
                    action_type="viewed",
                )
        except Exception:
            pass  # activity logging must never break profile loading

        return payload


@app.get("/api/v1/players/{player_id}/similar")
def player_similar(player_id: int, limit: int = Query(5, ge=1, le=10)):
    from app.queries.player_queries import get_player_profile
    from app.queries.similar_players import get_similar_players

    with session_scope() as db:
        if get_player_profile(db, player_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown player {player_id}")
        return get_similar_players(db, player_id, limit=limit)


# ---------------------------------------------------------------------------
# Phase 3 — trend / time-series (Part A)
# ---------------------------------------------------------------------------


@app.get("/api/v1/players/{player_id}/trend")
def player_trend(
    player_id: int,
    metric: str = Query(...),
    window: int = Query(5),
):
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
def player_event_coverage(player_id: int):
    from app.queries.event_queries import get_player_event_coverage

    return _with_session(get_player_event_coverage, player_id)


@app.get("/api/v1/players/{player_id}/events/matches")
def player_event_matches(
    player_id: int,
    competition: str | None = None,
    season: str | None = None,
):
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
):
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
):
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
def team_profile(league_slug: str, team_slug: str, season: str | None = None):
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


@app.get("/api/v1/coverage")
def coverage(league_id: int | None = None):
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


@app.get("/api/v1/positions")
def positions():
    meta = public_meta()
    from app.queries.leaderboard_queries import get_leaderboard_filtered

    with session_scope() as db:
        out = []
        for group in meta["position_groups"]:
            counts = {}
            for tier in ("tier_1", "tier_2", "tier_3"):
                res = get_leaderboard_filtered(
                    db,
                    metric=meta["index_metric_id"],
                    season="2025-26",
                    tier=tier,
                    position_group=group["code"],
                    limit=1,
                )
                counts[tier] = res["total"]
            out.append({**group, "qualifying_counts": counts})
        return out


@app.get("/api/v1/methodology")
def methodology():
    return public_meta()
