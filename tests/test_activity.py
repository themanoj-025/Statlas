"""Tests for app.activity — user activity logging with deduplication."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestActivityConstants:
    """Verify dedup window is configured."""

    def test_dedup_window(self) -> None:
        from app.activity import DEDUP_WINDOW_SECONDS
        assert DEDUP_WINDOW_SECONDS == 60


class TestLogActivity:
    """log_activity function signature and return type."""

    def test_function_exists(self) -> None:
        import inspect

        from app.activity import log_activity
        sig = inspect.signature(log_activity)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "user_id" in params
        assert "entity_type" in params
        assert "entity_id" in params
        assert "action_type" in params
        assert "metadata" in params

    def test_has_metadata_param(self) -> None:
        import inspect

        from app.activity import log_activity
        sig = inspect.signature(log_activity)
        assert sig.parameters["metadata"].default is None

    def test_return_annotation(self) -> None:
        import inspect

        from app.activity import log_activity
        sig = inspect.signature(log_activity)
        assert sig.return_annotation is not inspect.Parameter.empty
