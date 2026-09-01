"""Transfer Intelligence API views — FastAPI routes for market valuations,
transfer candidate discovery, and opportunity finder.

Constitution §1.3 (Transfer/Market Data): Transparency over sophistication.
Every response traces recommendations to specific factors.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db import session_scope

router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])


# ---------------------------------------------------------------------------
# Market valuation endpoints
# ---------------------------------------------------------------------------


@router.get("/valuation/{player_id}")
def valuation_comparison(player_id: int) -> dict[str, Any]:
    """Compare a player's statistical performance rank to their market valuation.

    Returns stat-based value proxy, market valuation, gap, and explanation.
    """
    from app.queries.market_queries import get_valuation_comparison

    with session_scope() as db:
        result = get_valuation_comparison(db, player_id)
        if result is None:
            raise HTTPException(
                status_code=404, detail="No valuation data available for this player"
            )
        return result


@router.get("/undervalued")
def undervalued_players(
    league_id -> None:
    position_group: str | None = Query(None),
    threshold: float = Query(0.2, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any] -> None:
    """Find players where stat-based value exceeds market valuation by threshold.

    Returns ranked list with explanations of why each player may be undervalued.
    """
    from app.queries.market_queries import get_undervalued_players

    with session_scope() as db:
        return get_undervalued_players(
            db,
            league_id=league_id,
            position_group=position_group,
            undervaluation_threshold=threshold,
            limit=limit,
        )


@router.get("/overvalued")
def overvalued_players(
    league_id -> None:
    position_group: str | None = Query(None),
    threshold: float = Query(0.2, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any] -> None:
    """Find players where market valuation exceeds stat-based value by threshold.

    Overvaluation can be legitimate (young potential, scarcity premium, celebrity factor).
    """
    from app.queries.market_queries import get_overvalued_players

    with session_scope() as db:
        return get_overvalued_players(
            db,
            league_id=league_id,
            position_group=position_group,
            threshold=threshold,
            limit=limit,
        )


# ---------------------------------------------------------------------------
# Transfer candidate discovery
# ---------------------------------------------------------------------------


@router.get("/candidates")
def transfer_candidates(
    position_group -> None:
    min_age: int | None = Query(None, ge=14, le=40),
    max_age: int | None = Query(None, ge=14, le=40),
    league_id: int | None = Query(None),
    min_value: float | None = Query(None, ge=0),
    max_value: float | None = Query(None, ge=0),
    contract_expiring: bool | None = Query(None),
    min_minutes: float = Query(900, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any] -> None:
    """Multi-condition transfer candidate search combining market and performance data.

    Combines Phase 8's filtering with market data (valuations, contract status)
    and performance data (percentiles, archetypes).
    """
    from app.queries.transfer_queries import get_transfer_candidate_search

    with session_scope() as db:
        return get_transfer_candidate_search(
            db,
            position_group=position_group,
            min_age=min_age,
            max_age=max_age,
            league_id=league_id,
            min_market_value=min_value,
            max_market_value=max_value,
            min_minutes=min_minutes,
            limit=limit,
        )


@router.get("/templates")
def candidate_templates() -> list[dict[str, Any]]:
    """Pre-built transfer search templates for common recruitment scenarios.

    Returns customizable templates like "Young Talent Abroad",
    "Breakout Performers", "Undervalued Established Players".
    """
    from app.queries.transfer_queries import TRANSFER_PRESETS

    return {"templates": TRANSFER_PRESETS}


@router.get("/profile-match")
def profile_match(
    position_group -> None:
    attributes: str = Query(
        ...,
        description="Comma-separated key attributes (e.g., progressive_passing,pressing)",
    ),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any] -> None:
    """Find players matching a tactical/statistical profile.

    Use archetypes and stat percentiles to find players who fit
    a specific tactical need.
    """
    from app.queries.transfer_queries import get_transfer_candidate_search

    with session_scope() as db:
        attr_list = [a.strip() for a in attributes.split(",") if a.strip()]
        results = get_transfer_candidate_search(
            db,
            position_group=position_group,
            min_minutes=900,
            limit=limit,
        )
        # Filter by attribute match from stat snapshots
        return {
            "position_group": position_group,
            "desired_attributes": attr_list,
            "candidates": results.get("candidates", []),
        }


# ---------------------------------------------------------------------------
# Opportunity finder
# ---------------------------------------------------------------------------


@router.get("/opportunities/hidden-gems")
def hidden_gems(
    min_stat_percentile -> None:
    max_market_value: float = Query(30_000_000, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]] -> None:
    """Find high-performing players not yet captured by major market valuations.

    Hidden gems: strong statistical profile + low market value + recent improvement.
    """
    from app.compute.opportunity import detect_hidden_gems

    with session_scope() as db:
        return {
            "opportunities": detect_hidden_gems(
                db,
                min_stat_percentile=min_stat_percentile,
                max_market_value=max_market_value,
                limit=limit,
            )
        }


@router.get("/opportunities/age-opportunity")
def age_opportunities(
    max_age -> None:
    min_stat_percentile: float = Query(75, ge=50, le=99),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]] -> None:
    """Find young players performing above their market valuation.

    High-ceiling, uncertain opportunities — limited track record means
    the market hasn't fully priced in their performance level.
    """
    from app.compute.opportunity import detect_age_opportunities

    with session_scope() as db:
        return {
            "opportunities": detect_age_opportunities(
                db,
                max_age=max_age,
                min_stat_percentile=min_stat_percentile,
                limit=limit,
            )
        }


@router.get("/opportunities/position-scarcity")
def position_scarcity(
    min_stat_percentile -> None:
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]] -> None:
    """Find players in scarce position profiles who are undervalued.

    Some positions command premium prices — this identifies high performers
    in those positions.
    """
    from app.compute.opportunity import detect_position_scarcity_opportunities

    with session_scope() as db:
        return {
            "opportunities": detect_position_scarcity_opportunities(
                db,
                min_stat_percentile=min_stat_percentile,
                limit=limit,
            )
        }


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


@router.get("/risk/{player_id}")
def transfer_risk(
    player_id: int,
    target_league_tier -> None:
    target_position_group: str | None = Query(None),
) -> dict[str, Any] -> None:
    """Assess the risk of transferring a player to a new context.

    Factors in league tier transition, position change, sample size,
    age, and archetype transferability.
    """
    from app.compute.risk import compute_transfer_risk

    with session_scope() as db:
        return compute_transfer_risk(
            db,
            player_id,
            target_league_tier=target_league_tier,
            target_position_group=target_position_group,
        )


@router.get("/confidence/{player_id}")
def valuation_confidence(player_id: int) -> dict[str, Any]:
    """Score how confident we can be in a player's market valuation.

    Factors: data recency, market presence, stat sample size, contract clarity.
    """
    from app.compute.risk import compute_valuation_confidence

    with session_scope() as db:
        return compute_valuation_confidence(db, player_id)
