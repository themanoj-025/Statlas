"""Dashboard domain models — activity log, dashboard state, saved players."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ACTION_TYPE_ENUM, ENTITY_TYPE_ENUM_13, Base


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(ENTITY_TYPE_ENUM_13, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(ACTION_TYPE_ENUM, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_activity_user_time", "user_id", "performed_at"),
        Index("ix_activity_entity", "user_id", "entity_type", "entity_id", "performed_at"),
    )


class DashboardState(Base):
    __tablename__ = "dashboard_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    widget_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dismissed_recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", name="uq_dashboard_state_user"),)


class SavedPlayer(Base):
    __tablename__ = "saved_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "player_id", name="uq_saved_player_user_player"),
        Index("ix_saved_players_user", "user_id", "saved_at"),
    )
