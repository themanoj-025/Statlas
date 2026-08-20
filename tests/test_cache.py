"""Tests for app.cache — InMemoryCacheBackend, @cached decorator, and fallback.

RedisCacheBackend is tested via mocks; InMemoryCacheBackend is tested directly.
"""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.cache import (
    InMemoryCacheBackend,
    RedisCacheBackend,
    cached,
    get_cache,
)


# ---------------------------------------------------------------------------
# InMemoryCacheBackend
# ---------------------------------------------------------------------------


class TestInMemoryCacheBackend:
    def test_set_and_get(self):
        cache = InMemoryCacheBackend()
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = InMemoryCacheBackend()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = InMemoryCacheBackend()
        cache.set("key1", "value1", ttl=60)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self):
        cache = InMemoryCacheBackend()
        cache.delete("nonexistent")  # should not raise

    def test_ttl_expiry(self):
        cache = InMemoryCacheBackend()
        cache.set("key1", "value1", ttl=0)  # expires immediately
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_overwrite_key(self):
        cache = InMemoryCacheBackend()
        cache.set("key1", "v1", ttl=60)
        cache.set("key1", "v2", ttl=60)
        assert cache.get("key1") == "v2"

    def test_delete_pattern_prefix(self):
        cache = InMemoryCacheBackend()
        cache.set("player:1:name", "Alice", ttl=60)
        cache.set("player:2:name", "Bob", ttl=60)
        cache.set("team:1:name", "Arsenal", ttl=60)

        cache.delete_pattern("player:*")

        assert cache.get("player:1:name") is None
        assert cache.get("player:2:name") is None
        assert cache.get("team:1:name") == "Arsenal"

    def test_delete_pattern_exact(self):
        cache = InMemoryCacheBackend()
        cache.set("exact_key", "value", ttl=60)
        cache.delete_pattern("exact_key")
        assert cache.get("exact_key") is None

    def test_get_returns_none_for_expired(self):
        """Expired entries should be cleaned up on access."""
        cache = InMemoryCacheBackend()
        cache._store["old"] = ("value", time.time() - 10)  # expired
        assert cache.get("old") is None
        assert "old" not in cache._store  # cleaned up

    def test_large_value(self):
        cache = InMemoryCacheBackend()
        big = "x" * 100_000
        cache.set("big", big, ttl=60)
        assert cache.get("big") == big


# ---------------------------------------------------------------------------
# RedisCacheBackend (mocked)
# ---------------------------------------------------------------------------


class TestRedisCacheBackend:
    def _make_backend(self):
        mock_redis = MagicMock()
        return RedisCacheBackend(mock_redis), mock_redis

    def test_set_calls_setex(self):
        backend, mock_redis = self._make_backend()
        backend.set("key1", "value1", ttl=300)
        mock_redis.setex.assert_called_once_with("key1", 300, "value1")

    def test_get_delegates_to_redis(self):
        backend, mock_redis = self._make_backend()
        mock_redis.get.return_value = "cached_value"
        assert backend.get("key1") == "cached_value"

    def test_delete(self):
        backend, mock_redis = self._make_backend()
        backend.delete("key1")
        mock_redis.delete.assert_called_once_with("key1")

    def test_delete_pattern_uses_scan(self):
        backend, mock_redis = self._make_backend()
        # First call: cursor=1, keys=["a:1", "a:2"]
        # Second call: cursor=0, keys=[]
        mock_redis.scan.side_effect = [
            (1, ["a:1", "a:2"]),
            (0, []),
        ]
        backend.delete_pattern("a:*")
        mock_redis.delete.assert_called_once_with("a:1", "a:2")


# ---------------------------------------------------------------------------
# @cached decorator
# ---------------------------------------------------------------------------


class TestCachedDecorator:
    def setup_method(self):
        import app.cache as cache_mod

        cache_mod._backend = InMemoryCacheBackend()

    def test_caches_return_value(self):
        call_count = 0

        @cached(ttl=60, prefix="test_cache_hit")
        def expensive_fn(_db, x):
            nonlocal call_count
            call_count += 1
            return {"result": x * 2}

        result1 = expensive_fn(None, 5)
        assert result1 == {"result": 10}
        assert call_count == 1

        # Second call should hit cache
        result2 = expensive_fn(None, 5)
        assert result2 == {"result": 10}
        assert call_count == 1  # not called again

    def test_different_args_different_cache_keys(self):
        call_count = 0

        @cached(ttl=60, prefix="test")
        def fn(_db, x):
            nonlocal call_count
            call_count += 1
            return x

        fn(None, 1)
        fn(None, 2)
        assert call_count == 2

    def test_none_result_not_cached(self):
        call_count = 0

        @cached(ttl=60, prefix="test")
        def fn(_db):
            nonlocal call_count
            call_count += 1
            return None

        fn(None)
        fn(None)
        assert call_count == 2  # None not cached, called both times

    def test_ttl_expiry(self):
        call_count = 0

        @cached(ttl=0, prefix="test")
        def fn(_db, x):
            nonlocal call_count
            call_count += 1
            return x

        fn(None, 1)
        assert call_count == 1

        time.sleep(0.05)
        fn(None, 1)
        assert call_count == 2  # expired, called again

    def test_preserves_function_name_and_doc(self):
        @cached(ttl=60, prefix="test")
        def my_documented_fn():
            """This is my docstring."""
            return 42

        assert my_documented_fn.__name__ == "my_documented_fn"
        assert my_documented_fn.__doc__ == "This is my docstring."

    def test_kwargs_in_cache_key(self):
        call_count = 0

        @cached(ttl=60, prefix="test")
        def fn(_db, *, metric="si_index", limit=10):
            nonlocal call_count
            call_count += 1
            return {"metric": metric, "limit": limit}

        fn(None, metric="si_index", limit=10)
        fn(None, metric="si_index", limit=20)  # different kwargs
        assert call_count == 2

    def test_json_serializable_values_cached(self):
        @cached(ttl=60, prefix="test")
        def fn(_db):
            return {"nested": {"data": [1, 2, 3]}}

        result = fn(None)
        assert result == {"nested": {"data": [1, 2, 3]}}

    def test_cache_hit_returns_deserialized_json(self):
        """Verify cache hit returns properly deserialized JSON, not a string."""
        @cached(ttl=60, prefix="test")
        def fn(_db):
            return {"key": "value"}

        result1 = fn(None)
        result2 = fn(None)
        assert result1 == result2
        assert isinstance(result2, dict)


# ---------------------------------------------------------------------------
# get_cache singleton
# ---------------------------------------------------------------------------


class TestGetCache:
    def setup_method(self):
        import app.cache as cache_mod

        cache_mod._backend = None

    def teardown_method(self):
        import app.cache as cache_mod

        cache_mod._backend = None

    def test_falls_back_to_in_memory(self):
        """Without Redis, get_cache returns InMemoryCacheBackend."""
        with patch.dict("sys.modules", {"redis": None}):
            result = get_cache()
            assert isinstance(result, InMemoryCacheBackend)

    def test_singleton_returns_same_instance(self):
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
