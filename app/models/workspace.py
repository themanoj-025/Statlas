"""Workspace domain models — shortlists, entries, notes, tags, status history."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    ENTRY_PRIORITY_ENUM,
    ENTRY_STATUS_ENUM,
    VISIBILITY_ENUM,
    Base,
)


class Shortlist(Base):
    __tablename__ = "shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    restricted_access: Mapped[list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (Index("ix_shortlists_user", "user_id"),)


class ShortlistEntry(Base):
    __tablename__ = "shortlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_id: Mapped[int] = mapped_column(ForeignKey("shortlists.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    status: Mapped[str] = mapped_column(ENTRY_STATUS_ENUM, nullable=False, default="discovered")
    priority: Mapped[str | None] = mapped_column(ENTRY_PRIORITY_ENUM, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    added_by_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("shortlist_id", "player_id", name="uq_shortlist_entry_player"),
        Index("ix_entries_shortlist", "shortlist_id"),
        Index("ix_entries_player", "player_id"),
        Index("ix_entries_status", "status"),
    )


class EntryNote(Base):
    __tablename__ = "entry_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_notes_entry", "shortlist_entry_id"),)


class EntryTag(Base):
    __tablename__ = "entry_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    tag_text: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("shortlist_entry_id", "tag_text", name="uq_entry_tag"),
        Index("ix_tags_entry", "shortlist_entry_id"),
    )


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(ENTRY_STATUS_ENUM, nullable=True)
    to_status: Mapped[str] = mapped_column(ENTRY_STATUS_ENUM, nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_status_history_entry", "shortlist_entry_id"),)
