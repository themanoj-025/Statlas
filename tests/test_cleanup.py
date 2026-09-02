"""Tests for app.cleanup — expired token and analytics cleanup."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestCleanupFunctions:
    """Verify cleanup functions exist and have correct signatures."""

    def test_cleanup_expired_tokens_exists(self) -> None:
        from app.cleanup import cleanup_expired_tokens
        import inspect
        sig = inspect.signature(cleanup_expired_tokens)
        assert "db" in sig.parameters

    def test_cleanup_old_analytics_exists(self) -> None:
        from app.cleanup import cleanup_old_analytics
        import inspect
        sig = inspect.signature(cleanup_old_analytics)
        assert "db" in sig.parameters
        assert "retention_days" in sig.parameters
        assert sig.parameters["retention_days"].default == 90

    def test_cleanup_return_type(self) -> None:
        from app.cleanup import cleanup_expired_tokens
        import inspect
        sig = inspect.signature(cleanup_expired_tokens)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_cleanup_old_analytics_return_type(self) -> None:
        from app.cleanup import cleanup_old_analytics
        import inspect
        sig = inspect.signature(cleanup_old_analytics)
        assert sig.return_annotation is not inspect.Parameter.empty
