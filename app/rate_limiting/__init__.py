"""Redis-backed rate limiter — production replacement for in-memory dicts.

Gracefully degrades to in-memory when Redis is unavailable (dev/test).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis as redis_lib

logger = logging.getLogger(__name__)

__all__ = [
    "RedisRateLimiter",
    "InMemoryRateLimiter",
    "get_rate_limiter",
]

# ---------------------------------------------------------------------------
# Redis-backed limiter (production)
# ---------------------------------------------------------------------------


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis INCR + EXPIRE."""

    def __init__(self, redis_client: "redis_lib.Redis", prefix: str = "ratelimit:"):
        self.redis = redis_client
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def is_limited(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        """Return True if the key has exceeded the rate limit."""
        rk = self._key(key)
        current = self.redis.incr(rk)
        if current == 1:
            self.redis.expire(rk, window_seconds)
        return current > max_attempts

    def get_remaining(self, key: str, max_attempts: int) -> int:
        """Remaining attempts before rate-limited."""
        rk = self._key(key)
        current = int(self.redis.get(rk) or 0)
        return max(0, max_attempts - current)

    def reset(self, key: str) -> None:
        """Reset rate limit for a key (e.g. after successful login)."""
        self.redis.delete(self._key(key))


# ---------------------------------------------------------------------------
# In-memory fallback (dev / test / no Redis)
# ---------------------------------------------------------------------------


class InMemoryRateLimiter:
    """Sliding-window rate limiter using a dict + monotonic clock.

    Sufficient for single-process dev/test; production should use Redis.
    """

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_limited(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = time.monotonic()
        window = [t for t in self._hits[key] if now - t < window_seconds]
        if len(window) >= max_attempts:
            self._hits[key] = window
            return True
        window.append(now)
        self._hits[key] = window
        return False

    def get_remaining(self, key: str, max_attempts: int, window_seconds: int = 60) -> int:
        now = time.monotonic()
        window = [t for t in self._hits.get(key, []) if now - t < window_seconds]
        return max(0, max_attempts - len(window))

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def reset_all(self) -> None:
        """Clear all rate-limit state (for test isolation)."""
        self._hits.clear()


# ---------------------------------------------------------------------------
# Module-level singleton — lazy initialised
# ---------------------------------------------------------------------------

_limiter: RedisRateLimiter | InMemoryRateLimiter | None = None


def get_rate_limiter() -> RedisRateLimiter | InMemoryRateLimiter:
    """Return the active rate limiter, creating it on first call.

    Falls back to InMemoryRateLimiter if Redis is unavailable.
    """
    global _limiter
    if _limiter is not None:
        return _limiter

    try:
        import redis as redis_lib

        from app.config import get_settings

        settings = get_settings()
        client = redis_lib.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_keepalive=True,
            health_check_interval=30,
        )
        client.ping()  # verify connectivity
        _limiter = RedisRateLimiter(client)
        logger.info("Using Redis-backed rate limiter (%s)", settings.redis_url)
    except Exception:
        logger.warning(
            "Redis unavailable — falling back to in-memory rate limiter "
            "(not suitable for multi-worker production)"
        )
        _limiter = InMemoryRateLimiter()

    return _limiter
