"""Watch domain models — watchlist, alerts, notification preferences."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    ALERT_TYPE_ENUM,
    DIGEST_FREQUENCY_ENUM,
    ENTITY_TYPE_ENUM,
    VISIBILITY_ENUM,
    Base,
)


class Watch(Base):
    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(ENTITY_TYPE_ENUM, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    followed_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    owner_org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(VISIBILITY_ENUM, nullable=False, default="personal")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_watch_entity"),
        Index("ix_watches_user", "user_id"),
        Index("ix_watches_entity", "entity_type", "entity_id"),
    )


class WatchAlert(Base):
    __tablename__ = "watch_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int] = mapped_column(ForeignKey("watches.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(ALERT_TYPE_ENUM, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    watch: Mapped[Watch] = relationship()

    __table_args__ = (
        UniqueConstraint("watch_id", "alert_type", "dedupe_key", name="uq_watch_alert_dedupe"),
        Index("ix_alerts_watch", "watch_id"),
        Index("ix_alerts_user_read", "dismissed", "read_at"),
    )


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_type_preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    digest_frequency: Mapped[str] = mapped_column(
        DIGEST_FREQUENCY_ENUM, nullable=False, default="immediate"
    )
    unsubscribe_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")

    __table_args__ = (UniqueConstraint("user_id", name="uq_preferences_user"),)
