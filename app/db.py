"""Database engine/session management.

Production: PostgreSQL via DATABASE_URL (schema in `schema.sql`).
Tests/dev: SQLite automatically when DATABASE_URL is unset — the ORM models use
dialect-neutral types (native_enum=False, JSON) so both work.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _make_engine() -> Engine:
    url = get_settings().database_url
    if url is None:
        # SQLite (tests / local dev without Postgres). StaticPool + check_same_thread
        # so in-memory databases survive across sessions within one process.
        return create_engine(
            "sqlite+pysqlite:///:memory:",
            poolclass=__import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_engine(url, pool_pre_ping=True)


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
