"""Player clustering & archetype discovery — backward-compatible re-exporter.

All implementation lives in ``clustering_pkg/`` as focused modules.
This file re-exports every public name so existing
``from app.compute.clustering import X`` continues to work unchanged.
"""

from app.compute.clustering_pkg import (
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
    assign_all_players,
    assign_player_to_archetype,
    build_feature_matrix,
    check_model_staleness,
    compute_cluster_centers,
    deploy_model,
    find_optimal_k,
    generate_archetype_definitions,
    get_monitoring_summary,
    rollback_model,
    train_clustering_model,
)

__all__ = [
    "ARCHETYPE_LABELS", "CHURN_ALERT_THRESHOLD", "CHURN_STRONG_THRESHOLD",
    "CLUSTERING_FEATURES", "CLUSTERING_MIN_MINUTES", "DEFAULT_N_CLUSTERS",
    "DRIFT_PVALUE_THRESHOLD", "MODEL_DIR", "OUTFIELD_POSITIONS",
    "SILHOUETTE_THRESHOLD", "STABILITY_AGREEMENT_THRESHOLD",
    "STABILITY_SIMILARITY_THRESHOLD", "AssignmentReport", "ClusteringReport",
    "assign_all_players", "assign_player_to_archetype", "build_feature_matrix",
    "check_model_staleness", "compute_cluster_centers", "deploy_model",
    "find_optimal_k", "generate_archetype_definitions",
    "get_monitoring_summary", "rollback_model", "train_clustering_model",
]
