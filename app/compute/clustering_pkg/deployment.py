"""Model deployment and rollback for clustering models."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import ClusteringModel

from .constants import SILHOUETTE_THRESHOLD

logger = logging.getLogger(__name__)


def deploy_model(db: Session, model_id: int) -> bool:
    """Deploy a model to production.

    Constitution Addendum §3.1: Every model update is a new version number.
    Constitution Addendum §1.4: Never deploy without a defined rollback plan.
    """
    model = db.get(ClusteringModel, model_id)
    if model is None:
        return False

    # Check silhouette score meets threshold
    if (
        model.silhouette_score is not None
        and model.silhouette_score < SILHOUETTE_THRESHOLD
    ):
        logger.warning(
            "Model %s v%s silhouette score %.3f below threshold %.3f — not deploying",
            model.model_name,
            model.version,
            model.silhouette_score,
            SILHOUETTE_THRESHOLD,
        )
        return False

    # Archive previous production model
    previous = db.query(ClusteringModel).filter_by(status="in_production").all()
    for prev in previous:
        prev.status = "archived"

    # Deploy new model
    model.status = "in_production"
    model.deployed_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Model %s v%s deployed to production", model.model_name, model.version)
    return True


def rollback_model(db: Session, model_name: str) -> bool:
    """Rollback to the previous production model.

    Constitution Addendum §1.4: If a model produces garbage, the system must
    have a quick path back to the previous version.
    """
    # Find the archived model (most recently archived)
    archived = (
        db.query(ClusteringModel)
        .filter_by(model_name=model_name, status="archived")
        .order_by(ClusteringModel.deployed_at.desc())
        .first()
    )
    if archived is None:
        logger.error("No archived model found for rollback: %s", model_name)
        return False

    # Archive current production
    current = (
        db.query(ClusteringModel)
        .filter_by(model_name=model_name, status="in_production")
        .all()
    )
    for c in current:
        c.status = "archived"

    # Re-deploy archived model
    archived.status = "in_production"
    archived.deployed_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Rolled back to %s v%s", model_name, archived.version)
    return True
