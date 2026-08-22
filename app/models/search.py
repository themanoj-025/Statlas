"""Search domain models — saved searches and search history."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import VISIBILITY_ENUM, Base


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (Index("ix_saved_searches_user", "user_id"),)


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_search_history_user", "user_id"),)
