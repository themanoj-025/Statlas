"""Structured logging with request IDs for production observability.

Provides:
- JSON-formatted log output (machine-readable, parseable by log aggregators)
- Per-request correlation ID via ContextVar
- A filter that injects request_id into every log record
"""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

# Per-request correlation ID — set by middleware, read by the filter.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject request_id from ContextVar into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatting and request-ID injection.

    Call once at application startup (app/api/main.py).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()

    try:
        from pythonjsonlogger import json as jsonlogger

        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    except ImportError:
        # Fallback to plain formatting if python-json-logger not installed
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s "
                "[req=%(request_id)s]",
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root.addHandler(handler)


def new_request_id() -> str:
    """Generate and set a new request ID. Returns the ID."""
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid
