"""
clustering_pkg — Focused modules for player clustering & archetype discovery.

Split from the monolithic ``clustering.py`` for maintainability.
The original ``clustering.py`` re-exports everything here.
"""

from app.compute.clustering_pkg.archetypes import (
    compute_cluster_centers,
    generate_archetype_definitions,
)
from app.compute.clustering_pkg.assignment import (
    assign_all_players,
    assign_player_to_archetype,
)
from app.compute.clustering_pkg.constants import (
    ARCHETYPE_LABELS,
    CHURN_ALERT_THRESHOLD,
    CHURN_STRONG_THRESHOLD,
    CLUSTERING_FEATURES,
    CLUSTERING_MIN_MINUTES,
    DEFAULT_N_CLUSTERS,
    DRIFT_PVALUE_THRESHOLD,
    MODEL_DIR,
    OUTFIELD_POSITIONS,
    SILHOUETTE_THRESHOLD,
    STABILITY_AGREEMENT_THRESHOLD,
    STABILITY_SIMILARITY_THRESHOLD,
    AssignmentReport,
    ClusteringReport,
)
from app.compute.clustering_pkg.data import build_feature_matrix
from app.compute.clustering_pkg.deployment import deploy_model, rollback_model
from app.compute.clustering_pkg.monitoring import (
    check_model_staleness,
    get_monitoring_summary,
)
from app.compute.clustering_pkg.training import find_optimal_k, train_clustering_model

__all__ = [
    "ARCHETYPE_LABELS",
    "CHURN_ALERT_THRESHOLD",
    "CHURN_STRONG_THRESHOLD",
    "CLUSTERING_FEATURES",
    "CLUSTERING_MIN_MINUTES",
    "DEFAULT_N_CLUSTERS",
    "DRIFT_PVALUE_THRESHOLD",
    "MODEL_DIR",
    "OUTFIELD_POSITIONS",
    "SILHOUETTE_THRESHOLD",
    "STABILITY_AGREEMENT_THRESHOLD",
    "STABILITY_SIMILARITY_THRESHOLD",
    "AssignmentReport",
    "ClusteringReport",
    "assign_all_players",
    "assign_player_to_archetype",
    "build_feature_matrix",
    "check_model_staleness",
    "compute_cluster_centers",
    "deploy_model",
    "find_optimal_k",
    "generate_archetype_definitions",
    "get_monitoring_summary",
    "rollback_model",
    "train_clustering_model",
]
