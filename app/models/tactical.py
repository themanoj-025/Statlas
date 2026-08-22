"""Tactical domain models — passing networks, spatial analysis, formations."""
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

from app.models.base import Base


class MatchPassingNetwork(Base):
    __tablename__ = "match_passing_networks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="full_match")
    network_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    style_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    anomalies_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id", "team_id", "phase", name="uq_passing_network_match_team_phase"
        ),
        Index("ix_passing_network_match", "match_id"),
    )


class MatchSpatialAnalysis(Base):
    __tablename__ = "match_spatial_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    analysis_type: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id", "team_id", "analysis_type", name="uq_spatial_analysis_match_team_type"
        ),
        Index("ix_spatial_analysis_match", "match_id"),
    )


class MatchFormation(Base):
    __tablename__ = "match_formations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    detected_formation: Mapped[str] = mapped_column(String(16), nullable=False)
    stability_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    conformity_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", name="uq_formation_match_team"),
        Index("ix_formation_match", "match_id"),
    )
