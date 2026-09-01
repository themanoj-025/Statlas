"""Feature matrix construction for player clustering."""

from __future__ import annotations

import logging

import numpy as np
from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import Player, StatSnapshot

from .constants import CLUSTERING_FEATURES, CLUSTERING_MIN_MINUTES, OUTFIELD_POSITIONS

logger = logging.getLogger(__name__)


def build_feature_matrix(
    db: Session,
    *,
    season: str | None = None,
    position_group: str | None = None,
    min_minutes: float = CLUSTERING_MIN_MINUTES,
) -> tuple[list[int], list[str], np.ndarray, list[dict]] -> None:
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
