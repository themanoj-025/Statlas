
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

"""Tests for app.rate_limiting — InMemoryRateLimiter and singleton fallback.

The Redis-backed limiter is tested via a mock; the in-memory limiter is tested
directly for correctness of the sliding-window algorithm.
"""

import time
from unittest.mock import MagicMock, patch

from app.rate_limiting import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter,
)

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# InMemoryRateLimiter
# ---------------------------------------------------------------------------


class TestInMemoryRateLimiter:
    def test_allows_under_threshold(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(4):
            assert not limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        assert limiter.get_remaining("user:1", max_attempts=5) == 1

    def test_blocks_at_threshold(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(5):
            limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        # 6th attempt should be blocked
        assert limiter.is_limited("user:1", max_attempts=5, window_seconds=60)

    def test_separate_keys_independent(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(5):
            limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        # user:2 should still be allowed
        assert not limiter.is_limited("user:2", max_attempts=5, window_seconds=60)

    def test_reset_clears_key(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(5):
            limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        assert limiter.is_limited("user:1", max_attempts=5, window_seconds=60)

        limiter.reset("user:1")

        assert not limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        assert limiter.get_remaining("user:1", max_attempts=5) == 4

    def test_get_remaining_zero_when_limited(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(10):
            limiter.is_limited("user:1", max_attempts=5, window_seconds=60)
        assert limiter.get_remaining("user:1", max_attempts=5) == 0

    def test_get_remaining_fresh_key(self) -> None:
        limiter = InMemoryRateLimiter()
        assert limiter.get_remaining("nonexistent", max_attempts=5) == 5

    def test_reset_nonexistent_key_no_error(self) -> None:
        limiter = InMemoryRateLimiter()
        limiter.reset("nonexistent")  # should not raise

    def test_window_expiry_allows_after_wait(self) -> None:
        """With a very short window, requests should become allowed again."""
        limiter = InMemoryRateLimiter()
        window = 0.1  # 100ms window

        for _ in range(3):
            limiter.is_limited("user:1", max_attempts=3, window_seconds=window)
        # Now blocked
        assert limiter.is_limited("user:1", max_attempts=3, window_seconds=window)

        # Wait for window to expire
        time.sleep(0.15)

        # Should be allowed again
        assert not limiter.is_limited("user:1", max_attempts=3, window_seconds=window)

    def test_zero_max_attempts_immediately_limited(self) -> None:
        limiter = InMemoryRateLimiter()
        assert limiter.is_limited("user:1", max_attempts=0, window_seconds=60)


# ---------------------------------------------------------------------------
# RedisRateLimiter (mocked)
# ---------------------------------------------------------------------------


class TestRedisRateLimiter:
    def _make_limiter(self) -> tuple[object, ...]:
        mock_redis = MagicMock()
        return RedisRateLimiter(mock_redis, prefix="test:"), mock_redis

    def test_is_limited_first_attempt_not_limited(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.incr.return_value = 1
        assert not limiter.is_limited("key1", max_attempts=5, window_seconds=60)
        mock_redis.incr.assert_called_once_with("test:key1")
        mock_redis.expire.assert_called_once_with("test:key1", 60)

    def test_is_limited_at_threshold(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.incr.return_value = 6
        assert limiter.is_limited("key1", max_attempts=5, window_seconds=60)
        # expire should NOT be called when count != 1
        mock_redis.expire.assert_not_called()

    def test_get_remaining(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.get.return_value = "3"
        assert limiter.get_remaining("key1", max_attempts=5) == 2

    def test_get_remaining_no_key(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.get.return_value = None
        assert limiter.get_remaining("key1", max_attempts=5) == 5

    def test_get_remaining_zero_when_limited(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.get.return_value = "5"
        assert limiter.get_remaining("key1", max_attempts=5) == 0

    def test_reset_deletes_key(self) -> None:
        limiter, mock_redis = self._make_limiter()
        limiter.reset("key1")
        mock_redis.delete.assert_called_once_with("test:key1")

    def test_key_prefix(self) -> None:
        limiter, mock_redis = self._make_limiter()
        mock_redis.incr.return_value = 1
        limiter.is_limited("mykey", max_attempts=5, window_seconds=60)
        mock_redis.incr.assert_called_once_with("test:mykey")


# ---------------------------------------------------------------------------
# Singleton / fallback
# ---------------------------------------------------------------------------


class TestGetRateLimiter:
    def setup_method(self) -> None:
        """Reset the module singleton before each test."""
        import app.rate_limiting as rl

        rl._limiter = None

    def teardown_method(self) -> None:
        """Reset the module singleton after each test."""
        import app.rate_limiting as rl


        rl._limiter = None

    def test_falls_back_to_in_memory_without_redis(self) -> None:
        """When Redis is unavailable, get_rate_limiter returns InMemoryRateLimiter."""

        # Patch redis to raise on import/ping
        with patch.dict("sys.modules", {"redis": None}):
            result = get_rate_limiter()
            assert isinstance(result, InMemoryRateLimiter)

    def test_singleton_returns_same_instance(self) -> None:
        """Calling get_rate_limiter twice returns the same object."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2
