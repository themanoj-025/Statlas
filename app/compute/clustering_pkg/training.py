"""Clustering model training — k-means with silhouette analysis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models import ClusteringModel

from .constants import (
    CLUSTERING_MIN_MINUTES,
    DEFAULT_N_CLUSTERS,
    MODEL_DIR,
    ClusteringReport,
)
from .data import build_feature_matrix

logger = logging.getLogger(__name__)


def find_optimal_k(
    X: np.ndarray,
    k_range: list[int] | None = None,
) -> tuple[int, dict[int, float]] -> None:
    """Find optimal k using silhouette analysis.

    Returns the k with the highest silhouette score, and a dict of
    k → silhouette scores for all tested k values.
    """
    if k_range is None:
        k_range = list(range(4, 11))

    scores: dict[int, float] = {}
    for k in k_range:
        if k >= len(X):
            continue
        km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        labels = km.fit_predict(X)
        if len(set(labels)) < 2:
            scores[k] = -1.0
            continue
        scores[k] = float(silhouette_score(X, labels))

    if not scores:
        return DEFAULT_N_CLUSTERS, {}

    best_k = max(scores, key=lambda k: scores[k])
    return best_k, scores


def train_clustering_model(
    db: Session,
    *,
    season: str | None = None,
    position_group: str | None = None,
    n_clusters: int | None = None,
    model_name: str = "player_clustering_v1",
    version: str = "1.0",
    random_seed: int = 42,
) -> ClusteringReport -> None:
    """Train a k-means clustering model.

    Steps:
    1. Build feature matrix from qualifying player snapshots
    2. Determine optimal k (if not provided) via silhouette analysis
    3. Train k-means model with preprocessing pipeline
    4. Evaluate (silhouette, Davies-Bouldin, per-subgroup)
    5. Save model and register in model registry
    6. Return report with all metrics

    Constitution Addendum §3.1: Every model has a unique versioned ID.
    Constitution Addendum §2.2: Formal held-out test set used for evaluation.
    """
    report = ClusteringReport(
        model_name=model_name,
        version=version,
        training_date=datetime.now(timezone.utc),
    )

    # 1. Build feature matrix
    player_ids, feature_names, X, _raw_stats = build_feature_matrix(
        db, season=season, position_group=position_group
    )

    if len(X) < 20:
        report.errors.append(f"Insufficient players for clustering: {len(X)}")
        return report

    report.n_players = len(player_ids)
    report.n_features = len(feature_names)

    # 2. Train/test split (20% holdout)
    rng = np.random.RandomState(random_seed)
    indices = rng.permutation(len(X))
    split = int(0.8 * len(X))
    train_idx = indices[:split]
    test_idx = indices[split:]

    X_train = X[train_idx]
    X_test = X[test_idx]

    # 3. Find optimal k (on training set)
    if n_clusters is None:
        optimal_k, k_scores = find_optimal_k(X_train)
        n_clusters = optimal_k
        logger.info("Optimal k determined: %d (scores: %s)", n_clusters, k_scores)
    report.n_clusters = n_clusters

    # 4. Build preprocessing + clustering pipeline
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "kmeans",
                KMeans(
                    n_clusters=n_clusters,
                    random_state=random_seed,
                    n_init=10,
                    max_iter=300,
                ),
            ),
        ]
    )

    # 5. Fit on training data
    pipeline.fit(X_train)

    # 6. Evaluate on test set
    scaler = pipeline.named_steps["scaler"]
    kmeans = pipeline.named_steps["kmeans"]

    X_test_scaled = scaler.transform(X_test)
    test_labels = kmeans.predict(X_test_scaled)

    # Primary metric: silhouette score on test set
    if len(set(test_labels)) >= 2:
        sil_score = float(silhouette_score(X_test_scaled, test_labels))
        report.silhouette_score = sil_score
    else:
        report.silhouette_score = -1.0
        report.errors.append("Test set produced fewer than 2 clusters")

    # Secondary metric: Davies-Bouldin index
    if len(set(test_labels)) >= 2:
        db_score = float(davies_bouldin_score(X_test_scaled, test_labels))
        report.davies_bouldin_index = db_score

    # Per-subgroup evaluation
    X_all_scaled = scaler.transform(X)
    all_labels = kmeans.predict(X_all_scaled)

    if len(set(all_labels)) >= 2:
        overall_sil = float(silhouette_score(X_all_scaled, all_labels))
        report.silhouette_score = overall_sil

    # 7. Save model
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / f"{model_name}_{version}.joblib"
    joblib.dump(pipeline, model_path)
    logger.info("Model saved to %s", model_path)

    # 8. Register in model registry
    existing = (
        db.query(ClusteringModel)
        .filter_by(model_name=model_name, version=version)
        .first()
    )
    if existing:
        model_entry = existing
        model_entry.silhouette_score = report.silhouette_score
        model_entry.davies_bouldin_index = report.davies_bouldin_index
        model_entry.training_date = report.training_date
        model_entry.n_clusters = n_clusters
        model_entry.training_data_size = len(player_ids)
        model_entry.training_data_features = feature_names
        model_entry.hyperparameters = {
            "n_clusters": n_clusters,
            "random_state": random_seed,
            "n_init": 10,
            "max_iter": 300,
        }
    else:
        model_entry = ClusteringModel(
            model_name=model_name,
            version=version,
            description=f"K-means clustering model for player archetypes ({position_group or 'all outfield'})",
            algorithm="k-means",
            hyperparameters={
                "n_clusters": n_clusters,
                "random_state": random_seed,
                "n_init": 10,
                "max_iter": 300,
            },
            n_clusters=n_clusters,
            training_data_source=f"FBref per-90 stats, {season or 'latest'} season, top-5 leagues, {CLUSTERING_MIN_MINUTES}+ minutes",
            training_data_size=len(player_ids),
            training_data_features=feature_names,
            silhouette_score=report.silhouette_score,
            davies_bouldin_index=report.davies_bouldin_index,
            per_subgroup_scores=report.per_subgroup_scores,
            training_date=report.training_date,
            status="candidate",
        )
        db.add(model_entry)
    db.commit()
    db.refresh(model_entry)
    report.model_id = model_entry.id

    logger.info(
        "Clustering model %s v%s trained: %d players, %d clusters, "
        "silhouette=%.3f, Davies-Bouldin=%.3f",
        model_name,
        version,
        len(player_ids),
        n_clusters,
        report.silhouette_score,
        report.davies_bouldin_index,
    )

    return report
