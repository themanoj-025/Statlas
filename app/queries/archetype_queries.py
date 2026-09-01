"""Archetype queries — read layer for player archetype data.

Constitution Addendum §1.2: Archetypes are explicitly labeled as patterns,
not predictions. This query layer serves archetype data for display.

Constitution Addendum §3.5: Every archetype output includes a real explanation
of what the cluster represents.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ArchetypeAssignment,
    ArchetypeDefinition,
    ClusteringModel,
    League,
    Player,
    StatSnapshot,
    Team,
)


def get_active_model(db: Session) -> dict[str, Any] | None:
    """Get the currently active clustering model."""
    model = (
        db.query(ClusteringModel)
        .filter_by(status="in_production")
        .order_by(ClusteringModel.deployed_at.desc())
        .first()
    )
    if model is None:
        return None
    return {
        "model_id": model.id,
        "model_name": model.model_name,
        "version": model.version,
        "algorithm": model.algorithm,
        "n_clusters": model.n_clusters,
        "silhouette_score": model.silhouette_score,
        "training_date": (
            model.training_date.isoformat() if model.training_date else None
        ),
        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        "training_data_source": model.training_data_source,
    }


def get_archetype_definitions(
    db: Session, model_id: int | None = None
) -> list[dict[str, Any]] -> None:
    """Get all archetype definitions for the active (or specified) model."""
    if model_id is None:
        model = (
            db.query(ClusteringModel)
            .filter_by(status="in_production")
            .order_by(ClusteringModel.deployed_at.desc())
            .first()
        )
        if model is None:
            return []
        model_id = model.id

    definitions = (
        db.query(ArchetypeDefinition)
        .filter_by(model_id=model_id)
        .order_by(ArchetypeDefinition.cluster_id)
        .all()
    )

    return [
        {
            "cluster_id": d.cluster_id,
            "name": d.name,
            "description": d.description,
            "player_count": d.player_count,
            "distinguishing_features": d.distinguishing_features,
            "example_players": d.example_players,
            "cluster_center": d.cluster_center,
        }
        for d in definitions
    ]


def get_player_archetype(
    db: Session,
    player_id: int,
    *,
    model_id: int | None = None,
) -> dict[str, Any] | None -> None:
    """Get the archetype assignment for a specific player.

    Returns archetype name, description, distance-to-center (typicality),
    and top distinguishing features with actual stat values vs archetype average.

    Constitution Addendum §3.5: Every archetype output has a real explanation.
    """
    # Get active model if not specified
    if model_id is None:
        model = (
            db.query(ClusteringModel)
            .filter_by(status="in_production")
            .order_by(ClusteringModel.deployed_at.desc())
            .first()
        )
        if model is None:
            return None
        model_id = model.id

    # Get latest assignment for this player
    assignment = (
        db.query(ArchetypeAssignment)
        .filter_by(player_id=player_id, model_id=model_id)
        .order_by(ArchetypeAssignment.snapshot_date.desc())
        .first()
    )
    if assignment is None:
        return None

    # Get archetype definition
    definition = (
        db.query(ArchetypeDefinition)
        .filter_by(model_id=model_id, cluster_id=assignment.cluster_id)
        .first()
    )

    # Get model info
    model = db.get(ClusteringModel, model_id)
    if model is None:
        return None

    # Compute typicality (inverse of distance — lower distance = more typical)
    # Normalize to 0-100 scale where 100 = perfectly at center
    typicality = max(0, min(100, 100 - (assignment.distance_to_center / 5.0 * 100)))

    return {
        "player_id": player_id,
        "model_version": model.version,
        "cluster_id": assignment.cluster_id,
        "archetype_name": (
            definition.name if definition else f"Cluster {assignment.cluster_id}"
        ),
        "archetype_description": definition.description if definition else "",
        "distance_to_center": assignment.distance_to_center,
        "typicality": round(typicality, 1),
        "is_outlier": assignment.is_outlier,
        "top_distinguishing_features": assignment.top_distinguishing_features,
        "computed_date": (
            assignment.computed_date.isoformat() if assignment.computed_date else None
        ),
        "snapshot_date": (
            assignment.snapshot_date.isoformat() if assignment.snapshot_date else None
        ),
    }


def get_archetype_players(
    db: Session,
    model_id: int,
    cluster_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any] -> None:
    """Get players in a specific archetype, sorted by distance to center (most typical first)."""
    # Get archetype definition
    definition = (
        db.query(ArchetypeDefinition)
        .filter_by(model_id=model_id, cluster_id=cluster_id)
        .first()
    )

    # Get assignments in this cluster
    query = (
        db.query(ArchetypeAssignment, Player)
        .join(Player, ArchetypeAssignment.player_id == Player.id)
        .filter(
            ArchetypeAssignment.model_id == model_id,
            ArchetypeAssignment.cluster_id == cluster_id,
        )
        .order_by(ArchetypeAssignment.distance_to_center)
    )

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    players = []
    for assignment, player in rows:
        team = db.get(Team, player.current_team_id) if player.current_team_id else None
        league = db.get(League, team.league_id) if team else None

        # Get latest snapshot for index score
        snap = (
            db.query(StatSnapshot)
            .filter(StatSnapshot.player_id == player.id)
            .order_by(StatSnapshot.scrape_date.desc())
            .first()
        )

        players.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": player.position_group,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "league_slug": league.slug if league else None,
                "distance_to_center": assignment.distance_to_center,
                "typicality": round(
                    max(0, min(100, 100 - (assignment.distance_to_center / 5.0 * 100))),
                    1,
                ),
                "top_distinguishing_features": assignment.top_distinguishing_features,
                "minutes_played": snap.minutes_played if snap else None,
            }
        )

    return {
        "model_id": model_id,
        "cluster_id": cluster_id,
        "archetype_name": definition.name if definition else f"Cluster {cluster_id}",
        "archetype_description": definition.description if definition else "",
        "total": total,
        "limit": limit,
        "offset": offset,
        "players": players,
    }


def get_archetype_overview(db: Session) -> dict[str, Any]:
    """Get a high-level overview of all archetypes for the active model.

    Returns archetype definitions with player counts and the model metadata.
    """
    model = (
        db.query(ClusteringModel)
        .filter_by(status="in_production")
        .order_by(ClusteringModel.deployed_at.desc())
        .first()
    )
    if model is None:
        return {
            "model": None,
            "archetypes": [],
            "total_players": 0,
        }

    definitions = (
        db.query(ArchetypeDefinition)
        .filter_by(model_id=model.id)
        .order_by(ArchetypeDefinition.cluster_id)
        .all()
    )

    total_players = sum(d.player_count for d in definitions)

    return {
        "model": {
            "model_id": model.id,
            "model_name": model.model_name,
            "version": model.version,
            "algorithm": model.algorithm,
            "n_clusters": model.n_clusters,
            "silhouette_score": model.silhouette_score,
            "training_date": (
                model.training_date.isoformat() if model.training_date else None
            ),
            "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        },
        "archetypes": [
            {
                "cluster_id": d.cluster_id,
                "name": d.name,
                "description": d.description,
                "player_count": d.player_count,
                "distinguishing_features": d.distinguishing_features[:3],
                "example_players": d.example_players[:3],
            }
            for d in definitions
        ],
        "total_players": total_players,
    }


def get_model_list(db: Session) -> list[dict[str, Any]]:
    """List all registered clustering models."""
    models = db.query(ClusteringModel).order_by(ClusteringModel.created_at.desc()).all()
    return [
        {
            "model_id": m.id,
            "model_name": m.model_name,
            "version": m.version,
            "status": m.status,
            "algorithm": m.algorithm,
            "n_clusters": m.n_clusters,
            "silhouette_score": m.silhouette_score,
            "training_date": m.training_date.isoformat() if m.training_date else None,
            "deployed_at": m.deployed_at.isoformat() if m.deployed_at else None,
            "training_data_size": m.training_data_size,
        }
        for m in models
    ]
