"""Tactical analysis API endpoints (Phase 17).

Coverage-gating (Constitution Never-List #8): every tactical endpoint first
checks that the match has sufficient event data before processing. No empty
or broken tactical views are served.

Attribution: StatsBomb data source must be credited on all rendered analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import session_scope

router = APIRouter(prefix="/api/v1/tactical", tags=["tactical"])


def _check_tactical_coverage(db, match_id: str, min_events: int = 100) -> None:
    """Raise 404 if match lacks sufficient event data for tactical analysis."""
    from app.compute.spatial_analysis import has_tactical_data

    coverage = has_tactical_data(db, match_id, min_events=min_events)
    if not coverage["has_coverage"]:
        raise HTTPException(
            status_code=404,
            detail=coverage["message"],
        )


# ---------------------------------------------------------------------------
# Passing networks
# ---------------------------------------------------------------------------

@router.get("/matches/{match_id}/passing-network")
def get_passing_network(
    match_id: str,
    phase: str = Query("full_match", description="full_match, first_half, second_half, open_play"),
    minute_start: float | None = None,
    minute_end: float | None = None,
):
    """Build and return the passing network for a match.

    Returns nodes (players with centrality metrics), edges (pass connections),
    tactical style detection, and anomaly flags.
    """
    from app.compute.passing_network import (
        build_passing_network,
        compute_network_metrics,
        detect_tactical_style,
        detect_network_anomalies,
    )

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)

        network = build_passing_network(
            db, match_id, phase=phase,
            minute_start=minute_start, minute_end=minute_end,
        )
        metrics = compute_network_metrics(network)
        style = detect_tactical_style(network, metrics)
        anomalies = detect_network_anomalies(network, metrics)

        return {
            "match_id": match_id,
            "phase": phase,
            "attribution": "Data by StatsBomb — open data",
            "network": {
                "nodes": metrics.get("nodes", []),
                "edges": network.get("edges", []),
                "total_passes": network.get("total_passes", 0),
            },
            "style": style,
            "anomalies": anomalies,
        }


@router.get("/matches/{match_id}/passing-network/cached")
def get_cached_passing_network(
    match_id: str,
    phase: str = Query("full_match"),
):
    """Retrieve a cached passing network (or compute and cache if missing)."""
    from app.compute.passing_network import (
        build_passing_network,
        compute_network_metrics,
        detect_tactical_style,
        detect_network_anomalies,
    )
    from app.models import MatchPassingNetwork

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)

        existing = (
            db.query(MatchPassingNetwork)
            .filter(
                MatchPassingNetwork.match_id == match_id,
                MatchPassingNetwork.phase == phase,
            )
            .first()
        )
        if existing:
            return {
                "match_id": match_id,
                "phase": phase,
                "cached": True,
                "computed_at": existing.computed_at.isoformat(),
                "network": existing.network_json,
                "metrics": existing.metrics_json,
                "style": existing.style_json,
                "anomalies": existing.anomalies_json,
            }

        # Compute and cache
        network = build_passing_network(db, match_id, phase=phase)
        metrics = compute_network_metrics(network)
        style = detect_tactical_style(network, metrics)
        anomalies = detect_network_anomalies(network, metrics)

        cache_row = MatchPassingNetwork(
            match_id=match_id,
            phase=phase,
            network_json={
                "nodes": metrics.get("nodes", []),
                "edges": network.get("edges", []),
                "total_passes": network.get("total_passes", 0),
            },
            metrics_json=metrics,
            style_json=style,
            anomalies_json=anomalies,
        )
        db.add(cache_row)
        db.commit()

        return {
            "match_id": match_id,
            "phase": phase,
            "cached": False,
            "network": cache_row.network_json,
            "metrics": cache_row.metrics_json,
            "style": cache_row.style_json,
            "anomalies": cache_row.anomalies_json,
        }


# ---------------------------------------------------------------------------
# Spatial analysis (heatmaps)
# ---------------------------------------------------------------------------

@router.get("/matches/{match_id}/pressure-map")
def get_pressure_map(
    match_id: str,
):
    """Get the pressure/defensive action heatmap for a match."""
    from app.compute.spatial_analysis import compute_pressure_heatmap

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)
        return compute_pressure_heatmap(db, match_id)


@router.get("/matches/{match_id}/possession-map")
def get_possession_map(
    match_id: str,
):
    """Get the possession density heatmap for a match."""
    from app.compute.spatial_analysis import compute_possession_heatmap

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)
        return compute_possession_heatmap(db, match_id)


@router.get("/matches/{match_id}/pressure-success")
def get_pressure_success(
    match_id: str,
):
    """Get pressure success rates per zone for a match."""
    from app.compute.spatial_analysis import compute_pressure_success

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)
        return compute_pressure_success(db, match_id)


@router.get("/matches/{match_id}/zones")
def get_zone_definitions(
    match_id: str,
):
    """Get zone definitions and a blank heatmap grid for the match."""
    from app.compute.spatial_analysis import ZONE_NAMES, assign_zone_name

    zones = list(ZONE_NAMES.values())
    return {
        "match_id": match_id,
        "zone_definitions": {
            name: {
                "row": i // 3,
                "col": i % 3,
                "label": name,
            }
            for i, name in enumerate(zones)
        },
        "columns": ["left", "center", "right"],
        "rows": ["defensive", "mid_defensive", "mid_attacking", "attacking"],
    }


# ---------------------------------------------------------------------------
# Formation analysis
# ---------------------------------------------------------------------------

@router.get("/matches/{match_id}/formation")
def get_formation(
    match_id: str,
    window_minutes: int = Query(15, ge=5, le=45),
):
    """Detect formation and track stability throughout the match.

    Returns the detected formation, stability analysis across time windows,
    and any detected formation changes.
    """
    from app.compute.formation import detect_formation, analyze_formation_stability

    with session_scope() as db:
        _check_tactical_coverage(db, match_id, min_events=50)

        formation = detect_formation(db, match_id)
        stability = analyze_formation_stability(
            db, match_id, window_minutes=window_minutes
        )

        return {
            "match_id": match_id,
            "attribution": "Data by StatsBomb — open data",
            "formation": formation,
            "stability": stability,
        }


@router.get("/matches/{match_id}/formation/conformity")
def get_formation_conformity(
    match_id: str,
    nominal: str | None = Query(None, description="Nominal formation, e.g. 4-3-3"),
):
    """Analyze how well players conform to their nominal formation roles."""
    from app.compute.formation import analyze_formation_conformity

    with session_scope() as db:
        _check_tactical_coverage(db, match_id, min_events=50)
        return analyze_formation_conformity(
            db, match_id, nominal_formation=nominal
        )


# ---------------------------------------------------------------------------
# Tactical match overview (all-in-one)
# ---------------------------------------------------------------------------

@router.get("/matches/{match_id}/overview")
def get_tactical_overview(
    match_id: str,
):
    """Complete tactical overview: passing network, heatmaps, and formation.

    Single endpoint for the tactical analysis page — combines all Phase 17
    analyses for a match into one response.
    """
    from app.compute.passing_network import (
        build_passing_network,
        compute_network_metrics,
        detect_tactical_style,
        detect_network_anomalies,
    )
    from app.compute.spatial_analysis import (
        compute_pressure_heatmap,
        compute_possession_heatmap,
    )
    from app.compute.formation import detect_formation, analyze_formation_stability

    with session_scope() as db:
        _check_tactical_coverage(db, match_id)

        # Passing network
        network = build_passing_network(db, match_id)
        metrics = compute_network_metrics(network)
        style = detect_tactical_style(network, metrics)
        anomalies = detect_network_anomalies(network, metrics)

        # Heatmaps
        pressure = compute_pressure_heatmap(db, match_id)
        possession = compute_possession_heatmap(db, match_id)

        # Formation
        formation = detect_formation(db, match_id)
        stability = analyze_formation_stability(db, match_id)

        return {
            "match_id": match_id,
            "attribution": "Data by StatsBomb — open data",
            "passing_network": {
                "nodes": metrics.get("nodes", []),
                "edges": network.get("edges", []),
                "total_passes": network.get("total_passes", 0),
            },
            "style": style,
            "anomalies": anomalies,
            "pressure_map": {
                "zone_densities": pressure["zone_densities"],
                "total_actions": pressure["total_actions"],
            },
            "possession_map": {
                "zone_densities": possession["zone_densities"],
                "total_actions": possession["total_actions"],
            },
            "formation": formation,
            "formation_stability": stability,
        }


# ---------------------------------------------------------------------------
# Coverage check
# ---------------------------------------------------------------------------

@router.get("/matches/{match_id}/coverage")
def check_tactical_coverage(
    match_id: str,
):
    """Check if tactical analysis is available for this match."""
    from app.compute.spatial_analysis import has_tactical_data

    with session_scope() as db:
        return has_tactical_data(db, match_id)



