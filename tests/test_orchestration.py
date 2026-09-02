"""Tests for app.orchestration — weekly refresh, event link, refresh helpers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestWeeklyRefresh:
    """Test weekly refresh orchestration module."""

    def test_module_importable(self) -> None:
        import app.orchestration.weekly_refresh as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.orchestration.weekly_refresh as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestEventLink:
    """Test event link module."""

    def test_module_importable(self) -> None:
        import app.orchestration.event_link as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.orchestration.event_link as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0


class TestRefreshHelpers:
    """Test refresh helpers module."""

    def test_module_importable(self) -> None:
        import app.orchestration.refresh_helpers as mod
        assert hasattr(mod, "__file__")

    def test_module_has_functions(self) -> None:
        import inspect

        import app.orchestration.refresh_helpers as mod
        funcs = [name for name, obj in inspect.getmembers(mod) if inspect.isfunction(obj)]
        assert len(funcs) > 0
