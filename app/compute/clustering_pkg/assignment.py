"""Player archetype assignment — assign players to nearest cluster."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session

from app.models import ArchetypeAssignment, ClusteringModel, Player, StatSnapshot

from .constants import (
    CHURN_ALERT_THRESHOLD,
    CLUSTERING_MIN_MINUTES,
    MODEL_DIR,
    OUTFIELD_POSITIONS,
    AssignmentReport,
)
from .data import build_feature_matrix
from .monitoring import _log_monitoring

logger = logging.getLogger(__name__)


def assign_player_to_archetype(
    db: Session,
    player_id: int,
    snapshot_date: datetime | None = None,
    model_id: int | None = None,
) -> dict[str, Any] | None:
    """Assign a player to the nearest archetype.

    Constitution Addendum §3.5: Every model output has a tested explanation.
    Returns archetype assignment, distance to center, and top distinguishing features.

    Returns None if:
    - Player has no qualifying snapshot
    - Model is stale (training data > 6 months old)
    - No model is in production
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc)

    # Get active model
    if model_id:
        model = db.get(ClusteringModel, model_id)
    else:
        model = (
            db.query(ClusteringModel)
            .filter_by(status="in_production")
            .order_by(ClusteringModel.deployed_at.desc())
            .first()
        )

    if model is None:
        return None

    # Staleness check (Constitution Addendum §3.2)
    if model.training_date:
        training_date = model.training_date
        if training_date.tzinfo is None:
            training_date = training_date.replace(tzinfo=timezone.utc)
        months_old = (datetime.now(timezone.utc) - training_date).days / 30
        if months_old > model.staleness_months:
            logger.warning(
                "Model %s v%s is stale (%.1f months old, threshold: %d)",
                model.model_name,
                model.version,
                months_old,
                model.staleness_months,
            )
            return None

    # Load model pipeline
    model_path = MODEL_DIR / f"{model.model_name}_{model.version}.joblib"
    if not model_path.exists():
        logger.error("Model file not found: %s", model_path)
        return None

    pipeline: Pipeline = joblib.load(model_path)

    # Get player's snapshot
    snap = (
        db.query(StatSnapshot)
        .filter(
            StatSnapshot.player_id == player_id,
            StatSnapshot.minutes_played >= CLUSTERING_MIN_MINUTES,
        )
        .order_by(StatSnapshot.scrape_date.desc())
        .first()
    )

    if snap is None:
        return None

    # Check player position is outfield
    player = db.get(Player, player_id)
    if player is None or player.position_group not in OUTFIELD_POSITIONS:
        return None

    # Extract features
    raw = snap.raw_stats or {}
    features = model.training_data_features
    if not all(f in raw for f in features):
        return None

    X = np.array([[float(raw[f]) for f in features]], dtype=np.float64)

    # Predict
    scaler = pipeline.named_steps["scaler"]
    kmeans = pipeline.named_steps["kmeans"]

    X_scaled = scaler.transform(X)
    cluster_id = int(kmeans.predict(X_scaled)[0])
    distance = float(np.linalg.norm(X_scaled - kmeans.cluster_centers_[cluster_id]))

    # Compute distinguishing features for this assignment
    center = kmeans.cluster_centers_[cluster_id]
    X_scaled_flat = X_scaled[0]
    feature_diffs = np.abs(X_scaled_flat - center)
    top_feature_indices = np.argsort(feature_diffs)[::-1][:3]

    # Inverse scale to get original values for explanation
    center_original = scaler.inverse_transform(kmeans.cluster_centers_)[cluster_id]

    distinguishing = [
        {
            "feature": features[idx],
            "player_value": round(float(X[0][idx]), 4),
            "archetype_average": round(float(center_original[idx]), 4),
        }
        for idx in top_feature_indices
    ]

    # Check if outlier (distance > 2x mean distance for this cluster)
    # For now, use a simple threshold
    is_outlier = distance > 3.0  # heuristic threshold in scaled space

    return {
        "player_id": player_id,
        "model_id": model.id,
        "model_version": model.version,
        "cluster_id": cluster_id,
        "distance_to_center": round(distance, 4),
        "top_distinguishing_features": distinguishing,
        "is_outlier": is_outlier,
        "snapshot_date": snap.scrape_date.isoformat(),
    }


def assign_all_players(
    db: Session,
    *,
    snapshot_date: datetime | None = None,
    model_id: int | None = None,
    season: str | None = None,
) -> AssignmentReport:
    """Assign all qualifying players to archetypes.

    Constitution Addendum §3.2: Log every inference for drift detection.
    """
    report = AssignmentReport()

    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc)

    # Get active model
    if model_id:
        model = db.get(ClusteringModel, model_id)
    else:
        model = (
            db.query(ClusteringModel)
            .filter_by(status="in_production")
            .order_by(ClusteringModel.deployed_at.desc())
            .first()
        )

    if model is None:
        report.errors.append("No model in production")
        return report

    report.model_id = model.id

    # Load model pipeline
    model_path = MODEL_DIR / f"{model.model_name}_{model.version}.joblib"
    if not model_path.exists():
        report.errors.append(f"Model file not found: {model_path}")
        return report

    pipeline: Pipeline = joblib.load(model_path)

    # Build feature matrix for all qualifying players
    player_ids, feature_names, X, _raw_stats = build_feature_matrix(db, season=season)

    if len(X) == 0:
        report.errors.append("No qualifying players found")
        return report

    # Get previous assignments for churn calculation
    previous_assignments = {}
    if model_id:
        prev_rows = (
            db.query(ArchetypeAssignment)
            .filter(
                ArchetypeAssignment.model_id == model.id,
                ArchetypeAssignment.snapshot_date < snapshot_date,
            )
            .order_by(ArchetypeAssignment.snapshot_date.desc())
            .all()
        )
        for row in prev_rows:
            if row.player_id not in previous_assignments:
                previous_assignments[row.player_id] = row.cluster_id

    # Predict
    scaler = pipeline.named_steps["scaler"]
    kmeans = pipeline.named_steps["kmeans"]

    X_scaled = scaler.transform(X)
    labels = kmeans.predict(X_scaled)
    distances = np.linalg.norm(X_scaled - kmeans.cluster_centers_[labels], axis=1)

    # Center in original space for distinguishing features
    centers_original = scaler.inverse_transform(kmeans.cluster_centers_)

    # Distribution tracking
    archetype_dist: dict[int, int] = defaultdict(int)
    churn_count = 0

    for i, pid in enumerate(player_ids):
        cid = int(labels[i])
        dist = float(distances[i])
        archetype_dist[cid] += 1

        # Compute distinguishing features
        center = kmeans.cluster_centers_[cid]
        feature_diffs = np.abs(X_scaled[i] - center)
        top_indices = np.argsort(feature_diffs)[::-1][:3]
        distinguishing = [
            {
                "feature": feature_names[idx],
                "player_value": round(float(X[i][idx]), 4),
                "archetype_average": round(float(centers_original[cid][idx]), 4),
            }
            for idx in top_indices
        ]

        is_outlier = dist > 3.0

        # Check churn
        if pid in previous_assignments and previous_assignments[pid] != cid:
            churn_count += 1

        # Upsert assignment (idempotent per player+model+snapshot)
        existing = (
            db.query(ArchetypeAssignment)
            .filter_by(
                player_id=pid,
                model_id=model.id,
                snapshot_date=snapshot_date,
            )
            .first()
        )
        if existing:
            existing.cluster_id = cid
            existing.distance_to_center = dist
            existing.top_distinguishing_features = distinguishing
            existing.is_outlier = is_outlier
        else:
            db.add(
                ArchetypeAssignment(
                    player_id=pid,
                    model_id=model.id,
                    cluster_id=cid,
                    distance_to_center=dist,
                    top_distinguishing_features=distinguishing,
                    snapshot_date=snapshot_date,
                    is_outlier=is_outlier,
                )
            )

        report.players_assigned += 1
        if is_outlier:
            report.players_outlier += 1

    db.commit()

    # Calculate churn rate
    if previous_assignments:
        report.previous_assignments = len(previous_assignments)
        report.churn_rate = churn_count / len(previous_assignments)
    report.archetype_distribution = dict(archetype_dist)

    # Log monitoring entry
    if report.churn_rate > CHURN_ALERT_THRESHOLD:
        _log_monitoring(
            db,
            model.id,
            "churn",
            f"Assignment churn rate {report.churn_rate:.1%} exceeds threshold",
            metric_name="churn_rate",
            metric_value=report.churn_rate,
            threshold=CHURN_ALERT_THRESHOLD,
            alert_triggered=True,
        )

    logger.info(
        "Archetype assignment: %d players assigned, %d outliers, churn=%.1f%%",
        report.players_assigned,
        report.players_outlier,
        report.churn_rate * 100,
    )

    return report
