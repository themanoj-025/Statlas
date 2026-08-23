"""Redis-backed caching layer with in-memory fallback.

Provides a simple get/set/delete interface for caching expensive queries.
Falls back to in-memory dict when Redis is unavailable.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

__all__ = [
    "CacheBackend",
    "RedisCacheBackend",
    "InMemoryCacheBackend",
    "get_cache",
    "cached",
    "invalidate_pattern",
]

T = TypeVar("T")


class CacheBackend:
    """Abstract cache interface."""

    def get(self, key: str) -> str | None:  # pragma: no cover
        raise NotImplementedError

    def set(self, key: str, value: str, ttl: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def delete(self, key: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def delete_pattern(self, pattern: str) -> None:  # pragma: no cover
        raise NotImplementedError


class RedisCacheBackend(CacheBackend):
    """Cache backed by Redis."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    def get(self, key: str) -> str | None:
        return self.redis.get(key)

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        self.redis.setex(key, ttl, value)

    def delete(self, key: str) -> None:
        self.redis.delete(key)

    def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern."""
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                self.redis.delete(*keys)
            if cursor == 0:
                break


class InMemoryCacheBackend(CacheBackend):
    """In-memory cache for dev/test (no Redis)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str) -> None:
        """Simple glob: handles trailing * only."""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]
        else:
            self._store.pop(pattern, None)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_backend: CacheBackend | None = None


def get_cache() -> CacheBackend:
    """Return the active cache backend, creating it on first call."""
    global _backend
    if _backend is not None:
        return _backend

    try:
        import redis as redis_lib

        from app.config import get_settings

        settings = get_settings()
        client = redis_lib.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        client.ping()
        _backend = RedisCacheBackend(client)
        logger.info("Using Redis cache backend")
    except Exception:
        logger.warning("Redis unavailable — using in-memory cache (dev/test only)")
        _backend = InMemoryCacheBackend()

    return _backend


def invalidate_pattern(pattern: str) -> int:
    """Delete all cache keys matching a glob pattern.

    Use after data mutations (e.g., new scrape run, admin update) to ensure
    stale cached responses are evicted. Returns the number of keys deleted.
    """
    cache = get_cache()
    try:
        if isinstance(cache, RedisCacheBackend):
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = cache.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += cache.redis.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        else:
            # In-memory: delegate to delete_pattern (count not available)
            before = len(cache._store)
            cache.delete_pattern(pattern)
            return before - len(cache._store)
    except Exception:
        logger.warning("Cache invalidation failed for pattern: %s", pattern)
        return 0


def cached(ttl: int = 3600, prefix: str = ""):
    """Decorator that caches a function's return value.

    Usage::

        @cached(ttl=3600, prefix="player")
        def get_player_profile(db, player_id):
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            # Build a cache key from function name + arguments (skip db/session args)
            key_parts = [prefix or func.__module__, func.__name__]
            for arg in args[1:]:  # skip first arg (db/session)
                key_parts.append(str(arg))
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            cache_key = ":".join(key_parts)

            # Try cache hit
            raw = cache.get(cache_key)
            if raw is not None:
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Cache miss — compute and store
            result = func(*args, **kwargs)
            if result is not None:
                try:
                    cache.set(cache_key, json.dumps(result, default=str), ttl)
                except Exception:
                    pass  # caching failure must never break the request
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
