"""Tests for app.api — API view modules."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestAnalyticsViews:
    """Test analytics API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.analytics_views import router
        assert router is not None


class TestBillingViews:
    """Test billing API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.billing_views import router
        assert router is not None


class TestDashboardViews:
    """Test dashboard API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.dashboard_views import router
        assert router is not None


class TestSearchViews:
    """Test search API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.search_views import router
        assert router is not None


class TestTacticalViews:
    """Test tactical API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.tactical_views import router
        assert router is not None


class TestTransferViews:
    """Test transfer API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.transfer_views import router
        assert router is not None


class TestWatchViews:
    """Test watch API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.watch_views import router
        assert router is not None


class TestWorkspaceViews:
    """Test workspace API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.workspace_views import router
        assert router is not None


class TestCommentViews:
    """Test comment API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.comment_views import router
        assert router is not None


class TestOrgViews:
    """Test org API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.org_views import router
        assert router is not None


class TestPublicViews:
    """Test public API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.public_views import router
        assert router is not None


class TestRegistryView:
    """Test registry API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.registry_view import router
        assert router is not None


class TestReportViews:
    """Test report API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.report_views import router
        assert router is not None


class TestArchetypeViews:
    """Test archetype API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.archetype_views import router
        assert router is not None


class TestAssistantViews:
    """Test assistant API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.assistant_views import router
        assert router is not None


class TestE2EViews:
    """Test E2E API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.e2e_views import router
        assert router is not None


class TestPlayerView:
    """Test player API view functions."""

    def test_module_has_router(self) -> None:
        from app.api.player_view import router
        assert router is not None


class TestAPIPlayers:
    """Test API players endpoints."""

    def test_module_has_router(self) -> None:
        from app.api.api_players import router
        assert router is not None


class TestAPITeams:
    """Test API teams endpoints."""

    def test_module_has_router(self) -> None:
        from app.api.api_teams import router
        assert router is not None


class TestAPILeagues:
    """Test API leagues endpoints."""

    def test_module_has_router(self) -> None:
        from app.api.api_leagues import router
        assert router is not None


class TestMiddleware:
    """Test API middleware."""

    def test_middleware_importable(self) -> None:
        import app.api.middleware
        assert hasattr(app.api.middleware, "__file__")


class TestAPIMain:
    """Test API main module."""

    def test_api_main_importable(self) -> None:
        import app.api.api_main
        assert hasattr(app.api.api_main, "__file__")
