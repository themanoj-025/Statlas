"""Statlas API — main FastAPI application.

Implementation split across:
- api_main.py: lifespan, OTEL tracing, error handlers, health endpoints
- api_leagues.py: league endpoints
- api_players.py: leaderboard and player endpoints
- api_teams.py: team, coverage, and meta endpoints
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.api_main import (
    health,
    lifespan,
    metrics,
    meta,
    readiness,
)

# Import routers from split modules
from app.api.api_leagues import router as leagues_router
from app.api.api_players import router as players_router
from app.api.api_teams import router as teams_router


app = FastAPI(
    title="Statlas API",
    version="1.0.0",
    description="Football player statistics and comparison platform",
    lifespan=lifespan,
)

# Health / meta (on main app)
app.add_api_route("/health", health, methods=["GET"])
app.add_api_route("/ready", readiness, methods=["GET"])
app.add_api_route("/meta", meta, methods=["GET"])
app.add_api_route("/metrics", metrics, methods=["GET"])

# Include routers
app.include_router(leagues_router)
app.include_router(players_router)
app.include_router(teams_router)


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError) -> Any:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def http_exception_handler(request: Request, exc: Exception) -> Any:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
