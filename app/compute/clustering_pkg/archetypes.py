"""Archetype definition — naming, interpretation, and cluster centers."""

from __future__ import annotations

import logging

import numpy as np
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session

from app.models import ArchetypeDefinition, Player

from .constants import ARCHETYPE_LABELS

logger = logging.getLogger(__name__)


def compute_cluster_centers(
    pipeline: Pipeline,
    X: np.ndarray,
    feature_names: list[str],
    player_ids: list[int],
    n_clusters: int,
) -> list[dict] -> None:
    """Compute cluster centers and identifying characteristics.

    For each cluster, returns:
    - cluster_id
    - center: mean feature values
    - distinguishing_features: top features that differ most from global mean
    - example_players: player IDs closest to center
    - player_count: number of players in cluster
    """
    scaler = pipeline.named_steps["scaler"]
    kmeans = pipeline.named_steps["kmeans"]

    X_scaled = scaler.transform(X)
    labels = kmeans.predict(X_scaled)
    centers_scaled = kmeans.cluster_centers_

    # Inverse transform to get centers in original feature space
    centers_original = scaler.inverse_transform(centers_scaled)

    # Global mean in original space
    global_mean = np.mean(X, axis=0)

    cluster_info = []
    for cid in range(n_clusters):
        mask = labels == cid
        center = centers_original[cid]
        player_ids_cluster = [player_ids[i] for i in np.where(mask)[0]]

        # Compute distinguishing features (top 5 by absolute difference from global mean)
        diffs = np.abs(center - global_mean)
        top_indices = np.argsort(diffs)[::-1][:5]
        distinguishing = [
            {
                "feature": feature_names[idx],
                "cluster_value": round(float(center[idx]), 4),
                "global_value": round(float(global_mean[idx]), 4),
                "difference": round(float(diffs[idx]), 4),
            }
            for idx in top_indices
        ]

        # Example players (closest to center by Euclidean distance)
        distances = np.linalg.norm(X_scaled[mask] - centers_scaled[cid], axis=1)
        closest_indices = np.argsort(distances)[:5]
        example_player_ids = [player_ids_cluster[i] for i in closest_indices]

        cluster_info.append(
            {
                "cluster_id": cid,
                "center": {
                    feature_names[i]: round(float(center[i]), 4)
                    for i in range(len(feature_names))
                },
                "distinguishing_features": distinguishing,
                "example_players": example_player_ids,
                "player_count": int(mask.sum()),
            }
        )

    return cluster_info


def generate_archetype_definitions(
    db: Session,
    model_id: int,
    cluster_info: list[dict],
    feature_names: list[str],
) -> list[dict] -> None:
    """Generate human-authored archetype definitions from cluster statistics.

    Constitution Addendum §1.3: Every archetype must be explainable.
    Names are based on distinguishing features, not arbitrary labels.
    """
    # Fetch player names for example players
    all_player_ids = set()
    for ci in cluster_info:
        all_player_ids.update(ci["example_players"])

    player_names = {}
    for pid in all_player_ids:
        player = db.get(Player, pid)
        if player:
            player_names[pid] = player.canonical_name

    definitions = []
    for ci in cluster_info:
        cid = ci["cluster_id"]
        distinguishing = ci["distinguishing_features"]

        # Generate name based on top distinguishing features
        name = _generate_archetype_name(distinguishing, feature_names)
        description = _generate_archetype_description(
            distinguishing, ci["player_count"]
        )

        # Fetch example player names
        examples = [
            {"player_id": pid, "name": player_names.get(pid, f"Player {pid}")}
            for pid in ci["example_players"]
        ]

        definitions.append(
            {
                "cluster_id": cid,
                "name": name,
                "description": description,
                "cluster_center": ci["center"],
                "distinguishing_features": ci["distinguishing_features"],
                "example_players": examples,
                "player_count": ci["player_count"],
            }
        )

        # Store in database
        existing = (
            db.query(ArchetypeDefinition)
            .filter_by(model_id=model_id, cluster_id=cid)
            .first()
        )
        if existing:
            existing.name = name
            existing.description = description
            existing.cluster_center = ci["center"]
            existing.distinguishing_features = ci["distinguishing_features"]
            existing.example_players = examples
            existing.player_count = ci["player_count"]
        else:
            db.add(
                ArchetypeDefinition(
                    model_id=model_id,
                    cluster_id=cid,
                    name=name,
                    description=description,
                    cluster_center=ci["center"],
                    distinguishing_features=ci["distinguishing_features"],
                    example_players=examples,
                    player_count=ci["player_count"],
                )
            )

    db.commit()
    return definitions


def _generate_archetype_name(
    distinguishing_features: list[dict], feature_names: list[str]
) -> str:
    """Generate a descriptive archetype name based on top distinguishing features."""
    if not distinguishing_features:
        return "Unknown Archetype"

    top = distinguishing_features[0]
    feature = top["feature"]
    cluster_val = top["cluster_value"]
    global_val = top["global_value"]

    label = ARCHETYPE_LABELS.get(feature, feature)

    if cluster_val > global_val:
        return f"High-{label}"
    else:
        return f"Low-{label}"


def _generate_archetype_description(
    distinguishing_features: list[dict], player_count: int
) -> str:
    """Generate a plain-language archetype description."""
    if not distinguishing_features:
        return "Archetype based on statistical clustering."

    parts = []
    for feat in distinguishing_features[:3]:
        feature = feat["feature"]
        cluster_val = feat["cluster_value"]
        global_val = feat["global_value"]

        label = ARCHETYPE_LABELS.get(feature, feature).lower()
        direction = "above" if cluster_val > global_val else "below"
        parts.append(f"{direction}-average {label}")

    description = f"Players in this archetype tend to have {', '.join(parts)} "
    description += "compared to the global average. "
    description += f"Based on {player_count} players in this cluster."

    return description
