"""Stats domain models — snapshots, percentiles, events, coverage, anomalies."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    COVERAGE_STATUS_ENUM,
    POSITION_GROUP_ENUM,
    QUEUE_STATUS_ENUM,
    SNAPSHOT_STATUS_ENUM,
    SOURCE_ENUM,
    TIER_ENUM,
    Base,
)


class StatSnapshot(Base):
    __tablename__ = "stat_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    scrape_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    raw_stats: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    minutes_played: Mapped[float] = mapped_column(Float, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        SNAPSHOT_STATUS_ENUM, nullable=False, default="ingested"
    )

    player = relationship("Player")
    team = relationship("Team")
    league = relationship("League")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "team_id", "league_id", "season", "source", "scrape_date",
            name="uq_stat_snapshot_natural_key",
        ),
        Index("ix_stat_snapshot_league_season_scrape", "league_id", "season", "scrape_date"),
        Index("ix_stat_snapshot_player", "player_id"),
        Index("ix_stat_snapshot_source", "source"),
    )


class PercentileSnapshot(Base):
    __tablename__ = "percentile_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("stat_snapshots.id"), nullable=False
    )
    computed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    position_group: Mapped[str] = mapped_column(POSITION_GROUP_ENUM, nullable=False)
    league_tier: Mapped[str] = mapped_column(TIER_ENUM, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    percentile_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "stat_snapshot_id", "metric_name", "league_tier",
            name="uq_percentile_snapshot_metric_tier",
        ),
        Index("ix_percentile_snapshot_published", "is_published"),
        Index("ix_percentile_snapshot_position_tier", "position_group", "league_tier"),
    )


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    x_coordinate: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_coordinate: Mapped[float | None] = mapped_column(Float, nullable=True)
    minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_competition_id: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[str | None] = mapped_column(String(16), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("match_id", "event_id", name="uq_match_event"),
        Index("ix_match_events_competition", "source_competition_id"),
        Index("ix_match_events_player", "player_id"),
    )


class DataCoverage(Base):
    __tablename__ = "data_coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"), nullable=True)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    seasons_available: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_successful_scrape: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(COVERAGE_STATUS_ENUM, nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint("source", "source_identifier", name="uq_coverage_source_identifier"),
        CheckConstraint(
            "league_id IS NOT NULL OR source = 'statsbomb'",
            name="ck_coverage_league_optional",
        ),
    )


class IngestionAnomaly(Base):
    __tablename__ = "ingestion_anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("stat_snapshots.id"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_anomalies_unresolved", "resolved"),)


class ReconciliationQueue(Base):
    __tablename__ = "reconciliation_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_record_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidate_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(QUEUE_STATUS_ENUM, nullable=False, default="pending")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "source_record_key", name="uq_queue_source_key"),
        Index("ix_queue_status", "status"),
    )
