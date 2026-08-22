"""Report domain models — AI scouting reports and quotas."""
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

from app.models.base import VISIBILITY_ENUM, Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    shortlist_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="generated")
    data_snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    verification_log: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (Index("ix_reports_user", "user_id"),)


class ReportQuota(Base):
    __tablename__ = "report_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reports_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reports_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_report_quota_period"),
    )
