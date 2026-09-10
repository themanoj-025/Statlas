"""Tests for the API application assembly (routers, middleware, deps, schemas)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class TestMainAPI:
    """The assembled application exposes its routers and routes."""

    def test_app_importable(self) -> None:
        from app.api.main import app

        assert app is not None

    def test_api_main_importable(self) -> None:
        from app.api.api_main import app

        assert app is not None

    def test_app_has_routes(self) -> None:
        from app.api.main import app

        assert len(app.routes) > 0

    def test_versioned_prefix_present(self) -> None:
        from app.api.main import app

        paths = {getattr(r, "path", "") for r in app.routes}
        assert any(p.startswith("/api/v1/") for p in paths)

    def test_health_route_registered(self) -> None:
        from app.api.main import app

        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/api/v1/health" in paths


class TestSchemas:
    """Public schema models validate and forbid unknown fields."""

    def test_error_response_schema(self) -> None:
        from app.api.schemas import ErrorResponse

        err = ErrorResponse(error={"code": "not_found", "message": "No such thing."})
        assert err.error.code == "not_found"

    def test_error_response_forbids_extra(self) -> None:
        from pydantic import ValidationError

        from app.api.schemas import ErrorResponse

        with pytest.raises(ValidationError):
            ErrorResponse.model_validate(
                {"error": {"code": "x", "message": "m", "extra": 1}}
            )

    def test_player_search_result_schema(self) -> None:
        from app.api.schemas import PlayerSearchResult

        result = PlayerSearchResult.model_validate(
            {
                "player_id": 1,
                "name": "Bukayo Saka",
                "position_group": "W",
            }
        )
        assert result.name == "Bukayo Saka"


class TestMiddleware:
    """Extracted middleware functions are registered on the app."""

    def test_body_size_limit_importable(self) -> None:
        from app.api.middleware import (
            MAX_REQUEST_BODY_BYTES,
            body_size_limit_middleware,
        )

        assert callable(body_size_limit_middleware)
        assert MAX_REQUEST_BODY_BYTES == 1 * 1024 * 1024

    def test_csrf_middleware_importable(self) -> None:
        from app.api.middleware import csrf_middleware

        assert callable(csrf_middleware)

    def test_rate_limit_middleware_importable(self) -> None:
        from app.api.middleware import security_and_rate_limit_middleware

        assert callable(security_and_rate_limit_middleware)

    def test_csrf_exempt_paths_include_webhook(self) -> None:
        from app.api.middleware import CSRF_EXEMPT_PATHS

        assert "/api/v1/billing/webhook" in CSRF_EXEMPT_PATHS


class TestDeps:
    """Shared auth dependency exists."""

    def test_require_user_importable(self) -> None:
        from app.api.deps import require_user, session_token

        assert callable(require_user)
        assert callable(session_token)


class TestBillingViews:
    """Billing router is exported and carries routes."""

    def test_billing_views_exist(self) -> None:
        from app.api.billing_views import router

        assert router is not None

    def test_billing_has_routes(self) -> None:
        from app.api.billing_views import router

        assert len(router.routes) > 0


class TestWatchViews:
    """Watch router is exported and carries routes."""

    def test_watch_views_exist(self) -> None:
        from app.api.watch_views import router

        assert router is not None

    def test_watch_has_routes(self) -> None:
        from app.api.watch_views import router

        assert len(router.routes) > 0
