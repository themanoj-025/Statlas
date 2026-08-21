"""
Shared structured JSON logging for production observability.

Features:
  - Structured JSON log file (rotated at 5 MB, 3 backups)
  - Human-readable console output
  - Extra context fields via ``extra`` dict
  - Request ID tracking for distributed tracing
  - Exception formatting with full tracebacks

Usage:
    from structured_logging import setup_logger
    log = setup_logger("my-service")
    log.info("Request started", extra={"request_id": "abc-123", "user_id": 42})
    log.error("Something broke")
"""

import json
import logging
import os
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

# Context variable for request ID tracking (works with async)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Cached loggers
_configured_loggers: set[str] = set()


class JSONFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON for structured ingestion.

    Every log line is a valid JSON object with ``timestamp``, ``level``,
    ``logger``, ``message``, ``request_id``, and any extra context keys.
    """

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add request ID from context variable
        req_id = request_id_var.get()
        if req_id:
            base["request_id"] = req_id

        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            base["exception"] = {
                "type": record.exc_info[0].__name__,
                "value": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        # Merge any extra context fields passed by the caller
        extra = getattr(record, "extra_fields", None)
        if extra:
            base.update(extra)

        return json.dumps(base, default=str, ensure_ascii=False)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    context: Optional[dict[str, Any]] = None,
) -> logging.Logger:
    """Get or create a logger with JSON file and console handlers.

    Parameters
    ----------
    name : str
        Logger name (e.g. ``"api"``, ``"worker"``).
    log_file : str, optional
        Log filename (e.g. ``"app.jsonl"``). Defaults to ``"{name}.jsonl"``.
    log_dir : str, optional
        Directory for log files. Defaults to ``"logs/"``.
    level : int
        Logging level (default ``logging.INFO``).
    context : dict, optional
        Static key-value pairs injected into every log line.

    Returns
    -------
    logging.Logger
    """
    if name in _configured_loggers:
        return logging.getLogger(name)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Determine log file path
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "logs")
    if log_file is None:
        log_file = f"{name}.jsonl"

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file_path = log_path / log_file

    # File handler (rotating, JSON format)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(console_handler)

    _configured_loggers.add(name)

    # Apply context if provided
    if context:
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            if not hasattr(record, "extra_fields"):
                record.extra_fields = {}
            record.extra_fields.update(context)
            return record

        logging.setLogRecordFactory(record_factory)

    return logger


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the current request ID in context. Returns the ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:12]
    request_id_var.set(request_id)
    return request_id


def shutdown() -> None:
    """Flush and close all logging handlers (call on app exit)."""
    logging.shutdown()
