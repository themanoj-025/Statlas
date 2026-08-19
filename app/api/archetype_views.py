"""Archetype API views — FastAPI routes for player archetype data.

Constitution Addendum §1.2: Archetypes are patterns, not predictions.
Every response includes explicit labeling that these are statistical patterns.

Constitution Addendum §3.5: Every archetype output has a real explanation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import session_scope

router = APIRouter(prefix="/api/v1/archetypes", tags=["archetypes"])


@router.get("")
def archetype_overview():
    """High-level overview of all player archetypes for the active model.

    Returns archetype definitions with player counts, descriptions, and
    the model metadata. This is the primary endpoint for the /archetypes page.
    """
    from app.queries.archetype_queries import get_archetype_overview

    with session_scope() as db:
        return get_archetype_overview(db)


@router.get("/models")
def model_list():
    """List all registered clustering models (including archived)."""
    from app.queries.archetype_queries import get_model_list

    with session_scope() as db:
        return {"models": get_model_list(db)}


@router.get("/model")
def active_model():
    """Get the currently active clustering model metadata."""
    from app.queries.archetype_queries import get_active_model

    with session_scope() as db:
        model = get_active_model(db)
        if model is None:
            raise HTTPException(status_code=404, detail="No active clustering model")
        return model


@router.get("/{cluster_id}")
def archetype_detail(cluster_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get players in a specific archetype, sorted by typicality.

    Returns the archetype definition and a paginated list of players
    assigned to this archetype.
    """
    from app.queries.archetype_queries import get_archetype_players, get_active_model

    with session_scope() as db:
        model = get_active_model(db)
        if model is None:
            raise HTTPException(status_code=404, detail="No active clustering model")

        result = get_archetype_players(
            db,
            model_id=model["model_id"],
            cluster_id=cluster_id,
            limit=limit,
        )

        if not result["players"] and result["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No archetype with cluster_id {cluster_id}",
            )

        return result


@router.get("/player/{player_id}")
def player_archetype(player_id: int):
    """Get the archetype assignment for a specific player.

    Returns archetype name, description, distance-to-center (typicality),
    and top distinguishing features with actual stat values vs archetype average.
    """
    from app.queries.archetype_queries import get_player_archetype

    with session_scope() as db:
        result = get_player_archetype(db, player_id)
        if result is None:
            return {
                "player_id": player_id,
                "archetype_name": None,
                "archetype_description": None,
                "cluster_id": None,
                "typicality": None,
                "is_outlier": None,
                "top_distinguishing_features": [],
                "note": "No archetype assignment available. This player may not have "
                        "sufficient qualifying data or no active clustering model exists.",
            }
        return result
