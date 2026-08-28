"""Lightweight circuit breaker for external API calls.

Usage:
    from circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    @breaker
    async def call_external_api():
        ...

State transitions:
    CLOSED -> OPEN: after failure_threshold consecutive failures
    OPEN -> HALF_OPEN: after recovery_timeout seconds
    HALF_OPEN -> CLOSED: on first success
    HALF_OPEN -> OPEN: on next failure
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker with configurable thresholds and recovery."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker %s: OPEN -> HALF_OPEN", self.name)
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("Circuit breaker %s: HALF_OPEN -> CLOSED", self.name)
        self._failure_count = 0
        self._success_count += 1

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker %s: OPEN (failures=%d)",
                self.name,
                self._failure_count,
            )

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        import functools

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.is_open():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN"
                )
            try:
                result = await fn(*args, **kwargs)
                self.record_success()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception:
                self.record_failure()
                raise

        return wrapper

    def __enter__(self) -> "CircuitBreaker":
        if self.is_open():
            raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure()


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is in OPEN state."""
