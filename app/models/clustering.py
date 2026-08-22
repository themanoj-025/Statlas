"""Clustering domain models — ML model registry, archetypes, monitoring."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
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

from app.models.base import CLUSTERING_STATUS_ENUM, Base


class ClusteringModel(Base):
    __tablename__ = "clustering_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    n_clusters: Mapped[int] = mapped_column(Integer, nullable=False)
    training_data_source: Mapped[str] = mapped_column(String(256), nullable=False)
    training_data_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    training_data_features: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    silhouette_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    davies_bouldin_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_subgroup_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    bias_audit_results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    training_code_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    training_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    staleness_months: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    status: Mapped[str] = mapped_column(CLUSTERING_STATUS_ENUM, nullable=False, default="candidate")
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    known_limitations: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_clustering_model_name_version"),
        Index("ix_clustering_model_status", "status"),
    )


class ArchetypeDefinition(Base):
    __tablename__ = "archetype_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("clustering_models.id"), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_center: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    distinguishing_features: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    example_players: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    model: Mapped[ClusteringModel] = relationship()

    __table_args__ = (
        UniqueConstraint("model_id", "cluster_id", name="uq_archetype_model_cluster"),
        Index("ix_archetype_model", "model_id"),
    )


class ArchetypeAssignment(Base):
    __tablename__ = "archetype_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("clustering_models.id"), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_to_center: Mapped[float] = mapped_column(Float, nullable=False)
    top_distinguishing_features: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    computed_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    player = relationship("Player")
    model: Mapped[ClusteringModel] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "player_id", "model_id", "snapshot_date",
            name="uq_archetype_assignment_player_model_date",
        ),
        Index("ix_archetype_assignment_player", "player_id"),
        Index("ix_archetype_assignment_model", "model_id", "cluster_id"),
    )


class ClusteringMonitoringLog(Base):
    __tablename__ = "clustering_monitoring_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("clustering_models.id"), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    log_type: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metric_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    model: Mapped[ClusteringModel] = relationship()

    __table_args__ = (
        Index("ix_monitoring_model_time", "model_id", "logged_at"),
        Index("ix_monitoring_alerts", "alert_triggered"),
    )
