"""Analytics domain models — events, sessions, metrics, cohorts, alerts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_analytics_event_name_time", "event_name", "created_at"),
        Index("ix_analytics_event_user", "user_id", "created_at"),
        Index("ix_analytics_event_session", "session_id", "created_at"),
    )


class AnalyticsSession(Base):
    __tablename__ = "analytics_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    device_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(32), nullable=True)
    os: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (Index("ix_session_user_time", "user_id", "started_at"),)


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("metric_date", "metric_name", "tier", name="uq_daily_metric"),
        Index("ix_daily_metric_name_date", "metric_name", "metric_date"),
    )


class FeatureUsage(Base):
    __tablename__ = "feature_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usage_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(64), nullable=False)
    adoption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_engagement_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("usage_date", "feature_name", name="uq_feature_usage"),
        Index("ix_feature_usage_date", "usage_date"),
    )


class CohortRetention(Base):
    __tablename__ = "cohort_retention"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_month: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    months_since_signup: Mapped[int] = mapped_column(Integer, nullable=False)
    cohort_size: Mapped[int] = mapped_column(Integer, nullable=False)
    retained_count: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_pct: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("cohort_month", "months_since_signup", name="uq_cohort_retention"),
        Index("ix_cohort_retention_month", "cohort_month"),
    )


class AnalyticsAlert(Base):
    __tablename__ = "analytics_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_alert_fired", "fired_at"),
        Index("ix_alert_name", "alert_name"),
    )


class AnalyticsAccessLog(Base):
    __tablename__ = "analytics_access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    dashboard_name: Mapped[str] = mapped_column(String(64), nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_access_log_user", "user_id", "accessed_at"),)
