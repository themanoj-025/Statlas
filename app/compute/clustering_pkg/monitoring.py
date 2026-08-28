"""Monitoring helpers for clustering models."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import ClusteringModel, ClusteringMonitoringLog

logger = logging.getLogger(__name__)


def _log_monitoring(
    db: Session,
    model_id: int,
    log_type: str,
    details: str,
    *,
    metric_name: str | None = None,
    metric_value: float | None = None,
    threshold: float | None = None,
    alert_triggered: bool = False,
) -> None:
    """Log a monitoring event."""
    db.add(
        ClusteringMonitoringLog(
            model_id=model_id,
            log_type=log_type,
            details={"message": details},
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            alert_triggered=alert_triggered,
        )
    )
    db.commit()


def check_model_staleness(db: Session, model_id: int) -> bool:
    """Check if a model is stale (training data > staleness_months old).

    Constitution Addendum §3.2: If staleness threshold exceeded, error loudly.
    """
    model = db.get(ClusteringModel, model_id)
    if model is None or model.training_date is None:
        return True  # treat as stale if no training date

    training_date = model.training_date
    if training_date.tzinfo is None:
        training_date = training_date.replace(tzinfo=timezone.utc)
    months_old = (datetime.now(timezone.utc) - training_date).days / 30
    if months_old > model.staleness_months:
        _log_monitoring(
            db,
            model_id,
            "alert",
            f"Model is {months_old:.1f} months old (threshold: {model.staleness_months} months)",
            metric_name="model_age_months",
            metric_value=months_old,
            threshold=float(model.staleness_months),
            alert_triggered=True,
        )
        return True
    return False


def get_monitoring_summary(db: Session, model_id: int) -> dict[str, Any]:
    """Get a summary of monitoring data for a model."""
    model = db.get(ClusteringModel, model_id)
    if model is None:
        return {"error": "Model not found"}

    logs = (
        db.query(ClusteringMonitoringLog)
        .filter_by(model_id=model_id)
        .order_by(ClusteringMonitoringLog.logged_at.desc())
        .limit(50)
        .all()
    )

    return {
        "model_id": model_id,
        "model_name": model.model_name,
        "version": model.version,
        "status": model.status,
        "silhouette_score": model.silhouette_score,
        "training_date": (
            model.training_date.isoformat() if model.training_date else None
        ),
        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        "recent_alerts": [
            {
                "log_type": log.log_type,
                "logged_at": log.logged_at.isoformat(),
                "details": log.details,
                "alert_triggered": log.alert_triggered,
            }
            for log in logs
            if log.alert_triggered
        ],
        "total_log_entries": len(logs),
    }
