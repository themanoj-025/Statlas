"""Database engine/session management.

Production: PostgreSQL via DATABASE_URL (schema in `schema.sql`).
Tests/dev: SQLite automatically when DATABASE_URL is unset — the ORM models use
dialect-neutral types (native_enum=False, JSON) so both work.
"""

from __future__ import annotations

import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _make_engine(url: str | None = None) -> Engine:
    if url is None:
        url = get_settings().database_url
    if url is None or "sqlite" in (url or ""):
        # SQLite (tests / local dev without Postgres). StaticPool + check_same_thread
        # so in-memory databases survive across sessions within one process.
        target_url = url or "sqlite+pysqlite:///:memory:"
        return create_engine(
            target_url,
            poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool,
            connect_args={"check_same_thread": False},
        )
    # PostgreSQL / MySQL — production-ready pooling.
    return create_engine(
        url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 10},
    )


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def session_scope() -> Session:
    """Return a new Session (caller closes it; or use as context manager)."""
    return get_session_factory()()


def dispose_engine() -> None:
    """Dispose the current engine and reset state. Useful for tests that
    need a fresh database connection."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _session_factory = None
    logger.debug("Database engine disposed and reset")


def create_schema() -> None:
    """Create tables from the ORM models.

    NOTE: production schemas are managed by `schema.sql` (the canonical DDL).
    This helper exists so tests can build a working SQLite database and so a
    fresh dev database can be created without running external tooling.
    """
    from app.models import (
        Base,  # local import to avoid a circular import at module load
    )

    Base.metadata.create_all(get_engine())
