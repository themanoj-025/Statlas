"""Statlas API — canonical application entry point.

Re-exports the fully built application from :mod:`app.api.api_main` (which
assembles all versioned routers, middleware, and health endpoints). This
module is kept as ``app.api.main`` so existing imports and tooling that use
``from app.api.main import app`` keep working.
"""

from __future__ import annotations

from app.api.api_main import app

__all__ = ["app"]
