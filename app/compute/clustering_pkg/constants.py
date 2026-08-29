"""Constants, feature definitions, and dataclasses for player clustering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Feature definitions (docs/ml/clustering-feature-engineering.md)
# ---------------------------------------------------------------------------

# Features used for clustering — real per-90 statistics, not derived metrics
CLUSTERING_FEATURES = [
    # Passing (registry IDs)
    "si_cmp_pct",
    "si_prgp_p90",
    # Carrying
    "si_prgc_p90",
    # Pressing
    "si_press_p90",
    # Defensive
    "si_tkl_p90",
    "si_int_p90",
    # Attacking
    "si_sh_p90",
    "si_xg_p90",
    "si_gls_p90",
    # Creation
    "si_kp_p90",
    "si_xag_p90",
    # Possession
    "si_dis_p90",
]

# Outfield position groups (exclude GK)
OUTFIELD_POSITIONS = {"CB", "FB", "DM", "CM", "AM", "W", "ST"}

# Minimum minutes for inclusion in clustering
CLUSTERING_MIN_MINUTES = 900

# Default number of clusters (will be overridden by silhouette analysis)
DEFAULT_N_CLUSTERS = 8

# Decision thresholds (docs/ml/clustering-model-selection.md)
SILHOUETTE_THRESHOLD = 0.30

# Model storage directory
MODEL_DIR = Path("data/models")

# Stability test: centroid similarity threshold
STABILITY_SIMILARITY_THRESHOLD = 0.95
STABILITY_AGREEMENT_THRESHOLD = 0.85

# Monitoring thresholds
CHURN_ALERT_THRESHOLD = 0.15
CHURN_STRONG_THRESHOLD = 0.20
DRIFT_PVALUE_THRESHOLD = 0.05


@dataclass
class ClusteringReport:
    """Report from a clustering training run."""

    model_id: int | None = None
    model_name: str = ""
    version: str = ""
    n_clusters: int = 0
    n_players: int = 0
    n_features: int = 0
    silhouette_score: float = 0.0
    davies_bouldin_index: float = 0.0
    per_subgroup_scores: dict[str, float] = field(default_factory=dict)
    per_league_scores: dict[str, float] = field(default_factory=dict)
    training_date: datetime | None = None
    stability_passed: bool = False
    interpretability_passed: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class AssignmentReport:
    """Report from an archetype assignment run."""

    model_id: int = 0
    players_assigned: int = 0
    players_outlier: int = 0
    previous_assignments: int = 0
    churn_rate: float = 0.0
    archetype_distribution: dict[int, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# Human-readable labels for archetype naming and descriptions (single source of truth).
ARCHETYPE_LABELS: dict[str, str] = {
    "si_cmp_pct": "Pass Completion",
    "si_prgp_p90": "Progressive Passing",
    "si_prgc_p90": "Ball Carrying",
    "si_press_p90": "Pressing",
    "si_tkl_p90": "Tackling",
    "si_int_p90": "Interceptions",
    "si_sh_p90": "Shooting",
    "si_xg_p90": "Expected Goals",
    "si_gls_p90": "Goals",
    "si_kp_p90": "Key Passing",
    "si_xag_p90": "Expected Assists",
    "si_dis_p90": "Dispossessed",
}
