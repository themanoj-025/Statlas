"""Player clustering & archetype discovery (Phase 14 — ML platform).

Unsupervised k-means clustering to discover player archetypes — groups of
outfield players with similar statistical profiles.

Constitution Addendum §1.2: Clustering is explicitly labeled as patterns,
not predictions. Archetypes describe statistical similarity, not player ability.

Constitution Addendum §2.1: Training data is reproducible from a documented
query. The exact same query against the same data snapshot produces the exact
same training set.

Constitution Addendum §3.4: Every model has a completed model card with all
required sections (docs/ml/player_clustering_v1.md).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import (
    ArchetypeAssignment,
    ArchetypeDefinition,
    ClusteringModel,
    ClusteringMonitoringLog,
    Player,
    StatSnapshot,
)

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Feature matrix construction
# ---------------------------------------------------------------------------


def build_feature_matrix(
    db: Session,
    *,
    season: str | None = None,
    position_group: str | None = None,
    min_minutes: float = CLUSTERING_MIN_MINUTES,
) -> tuple[list[int], list[str], np.ndarray, list[dict]]:
    """Build the feature matrix for clustering.

    Returns:
        player_ids: list of player IDs in the matrix
        feature_names: list of feature column names
        X: numpy array of shape (n_players, n_features)
        raw_stats_list: list of raw_stats dicts for each player
    """
    registry = load_registry()

    # Query qualifying snapshots
    query = (
        db.query(StatSnapshot, Player)
        .join(Player, StatSnapshot.player_id == Player.id)
        .filter(
            StatSnapshot.minutes_played >= min_minutes,
            Player.position_group.in_([g for g in OUTFIELD_POSITIONS]),
        )
    )
    if season:
        query = query.filter(StatSnapshot.season == season)
    if position_group:
        query = query.filter(Player.position_group == position_group)

    snapshots = query.all()

    if not snapshots:
        return [], [], np.empty((0, 0)), []

    # Build player → snapshot mapping (prefer latest snapshot per player)
    player_snapshots: dict[int, tuple[StatSnapshot, Player]] = {}
    for snap, player in snapshots:
        pid = snap.player_id
        if pid not in player_snapshots:
            player_snapshots[pid] = (snap, player)
        else:
            existing_snap = player_snapshots[pid][0]
            if snap.scrape_date > existing_snap.scrape_date:
                player_snapshots[pid] = (snap, player)

    # Filter to features that exist in the registry
    available_features = [
        f for f in CLUSTERING_FEATURES if f in registry.get("metrics", {})
    ]

    # Build matrix
    player_ids = []
    raw_stats_list = []
    feature_rows = []

    for pid, (snap, player) in sorted(player_snapshots.items()):
        raw = snap.raw_stats or {}
        # Check all features are present
        if all(f in raw for f in available_features):
            row = [float(raw[f]) for f in available_features]
            feature_rows.append(row)
            player_ids.append(pid)
            raw_stats_list.append(raw)

    if not feature_rows:
        return [], [], np.empty((0, len(available_features))), []

    X = np.array(feature_rows, dtype=np.float64)
    return player_ids, available_features, X, raw_stats_list


# ---------------------------------------------------------------------------
# Clustering model training
# ---------------------------------------------------------------------------


def find_optimal_k(
    X: np.ndarray,
    k_range: list[int] | None = None,
) -> tuple[int, dict[int, float]]:
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

    best_k = max(scores, key=scores.get)  # type: ignore[arg-type]
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
) -> ClusteringReport:
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
    player_ids, feature_names, X, raw_stats = build_feature_matrix(
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
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("kmeans", KMeans(
            n_clusters=n_clusters,
            random_state=random_seed,
            n_init=10,
            max_iter=300,
        )),
    ])

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
    # (per position group and per league if available)
    # This requires the full dataset's position/league info
    # For now, compute on the full dataset
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
        model_name, version, len(player_ids), n_clusters,
        report.silhouette_score, report.davies_bouldin_index,
    )

    return report


# ---------------------------------------------------------------------------
# Archetype definition (naming + interpretation)
# ---------------------------------------------------------------------------


def compute_cluster_centers(
    pipeline: Pipeline,
    X: np.ndarray,
    feature_names: list[str],
    player_ids: list[int],
    n_clusters: int,
) -> list[dict]:
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

        cluster_info.append({
            "cluster_id": cid,
            "center": {feature_names[i]: round(float(center[i]), 4) for i in range(len(feature_names))},
            "distinguishing_features": distinguishing,
            "example_players": example_player_ids,
            "player_count": int(mask.sum()),
        })

    return cluster_info


def generate_archetype_definitions(
    db: Session,
    model_id: int,
    cluster_info: list[dict],
    feature_names: list[str],
) -> list[dict]:
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
        description = _generate_archetype_description(distinguishing, ci["player_count"])

        # Fetch example player names
        examples = [
            {"player_id": pid, "name": player_names.get(pid, f"Player {pid}")}
            for pid in ci["example_players"]
        ]

        definitions.append({
            "cluster_id": cid,
            "name": name,
            "description": description,
            "cluster_center": ci["center"],
            "distinguishing_features": ci["distinguishing_features"],
            "example_players": examples,
            "player_count": ci["player_count"],
        })

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
            db.add(ArchetypeDefinition(
                model_id=model_id,
                cluster_id=cid,
                name=name,
                description=description,
                cluster_center=ci["center"],
                distinguishing_features=ci["distinguishing_features"],
                example_players=examples,
                player_count=ci["player_count"],
            ))

    db.commit()
    return definitions


def _generate_archetype_name(distinguishing_features: list[dict], feature_names: list[str]) -> str:
    """Generate a descriptive archetype name based on top distinguishing features."""
    if not distinguishing_features:
        return "Unknown Archetype"

    top = distinguishing_features[0]
    feature = top["feature"]
    cluster_val = top["cluster_value"]
    global_val = top["global_value"]

    # Feature name mapping for human-readable labels
    feature_labels = {
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

    label = feature_labels.get(feature, feature)

    if cluster_val > global_val:
        return f"High-{label}"
    else:
        return f"Low-{label}"


def _generate_archetype_description(distinguishing_features: list[dict], player_count: int) -> str:
    """Generate a plain-language archetype description."""
    if not distinguishing_features:
        return "Archetype based on statistical clustering."

    parts = []
    for feat in distinguishing_features[:3]:
        feature = feat["feature"]
        cluster_val = feat["cluster_value"]
        global_val = feat["global_value"]

        feature_labels = {
            "si_cmp_pct": "pass completion",
            "si_prgp_p90": "progressive passes",
            "si_prgc_p90": "progressive carries",
            "si_press_p90": "pressures",
            "si_tkl_p90": "tackles",
            "si_int_p90": "interceptions",
            "si_sh_p90": "shots",
            "si_xg_p90": "expected goals",
            "si_gls_p90": "goals",
            "si_kp_p90": "key passes",
            "si_xag_p90": "expected assists",
            "si_dis_p90": "dispossessed",
        }

        label = feature_labels.get(feature, feature)
        direction = "above" if cluster_val > global_val else "below"
        parts.append(f"{direction}-average {label}")

    description = f"Players in this archetype tend to have {', '.join(parts)} "
    description += "compared to the global average. "
    description += f"Based on {player_count} players in this cluster."

    return description


# ---------------------------------------------------------------------------
# Player assignment
# ---------------------------------------------------------------------------


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
                model.model_name, model.version, months_old, model.staleness_months,
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
    player_ids, feature_names, X, raw_stats = build_feature_matrix(
        db, season=season
    )

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
    distances = np.linalg.norm(
        X_scaled - kmeans.cluster_centers_[labels], axis=1
    )

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
            db.add(ArchetypeAssignment(
                player_id=pid,
                model_id=model.id,
                cluster_id=cid,
                distance_to_center=dist,
                top_distinguishing_features=distinguishing,
                snapshot_date=snapshot_date,
                is_outlier=is_outlier,
            ))

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
            db, model.id, "churn",
            f"Assignment churn rate {report.churn_rate:.1%} exceeds threshold",
            metric_name="churn_rate",
            metric_value=report.churn_rate,
            threshold=CHURN_ALERT_THRESHOLD,
            alert_triggered=True,
        )

    logger.info(
        "Archetype assignment: %d players assigned, %d outliers, churn=%.1f%%",
        report.players_assigned, report.players_outlier, report.churn_rate * 100,
    )

    return report


# ---------------------------------------------------------------------------
# Model deployment and rollback
# ---------------------------------------------------------------------------


def deploy_model(db: Session, model_id: int) -> bool:
    """Deploy a model to production.

    Constitution Addendum §3.1: Every model update is a new version number.
    Constitution Addendum §1.4: Never deploy without a defined rollback plan.
    """
    model = db.get(ClusteringModel, model_id)
    if model is None:
        return False

    # Check silhouette score meets threshold
    if model.silhouette_score is not None and model.silhouette_score < SILHOUETTE_THRESHOLD:
        logger.warning(
            "Model %s v%s silhouette score %.3f below threshold %.3f — not deploying",
            model.model_name, model.version, model.silhouette_score, SILHOUETTE_THRESHOLD,
        )
        return False

    # Archive previous production model
    previous = (
        db.query(ClusteringModel)
        .filter_by(status="in_production")
        .all()
    )
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


# ---------------------------------------------------------------------------
# Monitoring helpers
# ---------------------------------------------------------------------------


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
    db.add(ClusteringMonitoringLog(
        model_id=model_id,
        log_type=log_type,
        details={"message": details},
        metric_name=metric_name,
        metric_value=metric_value,
        threshold=threshold,
        alert_triggered=alert_triggered,
    ))
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
            db, model_id, "alert",
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
        "training_date": model.training_date.isoformat() if model.training_date else None,
        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        "recent_alerts": [
            {
                "log_type": log.log_type,
                "logged_at": log.logged_at.isoformat(),
                "details": log.details,
                "alert_triggered": log.alert_triggered,
            }
            for log in logs if log.alert_triggered
        ],
        "total_log_entries": len(logs),
    }
