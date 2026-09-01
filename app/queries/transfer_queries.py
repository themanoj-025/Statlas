"""Transfer candidate discovery — multi-condition search combining
market, performance, and profile data.

Constitution §3: Every claim backed by real data. Candidate recommendations
must be explainable to a club's recruitment board.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ContractStatus,
    League,
    MarketValuation,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)


def get_contract_situation_score(
    db: Session,
    player_id: int,
    *,
    reference_date: datetime | None = None,
) -> dict[str, Any] | None:
    """Score a player's contract situation for transfer feasibility.

    Players with expiring contracts are more available/cheaper to acquire.

    Returns:
    - availability_score: 0-100 (higher = more available)
    - contract_status: human-readable status
    - years_remaining: approximate years until contract end
    - salary_annual_eur: annual salary if available
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    latest = (
        db.query(ContractStatus)
        .filter(ContractStatus.player_id == player_id)
        .order_by(ContractStatus.snapshot_date.desc())
        .first()
    )

    if latest is None:
        return {
            "player_id": player_id,
            "availability_score": 50,
            "contract_status": "unknown",
            "contract_status_label": "Unknown",
            "years_remaining": None,
            "salary_annual_eur": None,
            "note": "No contract data available — availability cannot be assessed",
        }

    years_remaining = None
    if latest.contract_end_date:
        years_remaining = max(
            0,
            (latest.contract_end_date.year - reference_date.year)
            + (1 if latest.contract_end_date.month > reference_date.month else 0),
        )

    # Availability scoring
    if latest.contract_status == "expired":
        availability = 95  # Free agent — maximum availability
    elif latest.contract_status == "expiring_next_season":
        availability = 85  # Can sign pre-contract or buy cheap
    elif years_remaining is not None and years_remaining <= 1:
        availability = 80
    elif years_remaining is not None and years_remaining <= 2:
        availability = 60
    elif years_remaining is not None and years_remaining <= 3:
        availability = 40
    else:
        availability = 20  # Locked in — hard to get

    status_label = latest.contract_status.replace("_", " ").title()
    if years_remaining is not None:
        status_label += f" ({years_remaining}yr remaining)"

    return {
        "player_id": player_id,
        "availability_score": availability,
        "contract_status": latest.contract_status,
        "contract_status_label": status_label,
        "years_remaining": years_remaining,
        "contract_end_date": (
            latest.contract_end_date.isoformat() if latest.contract_end_date else None
        ),
        "salary_annual_eur": latest.contract_value_per_year_eur,
    }


def get_transfer_candidate_search(
    db: Session,
    *,
    position_group: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    min_market_value: float | None = None,
    max_market_value: float | None = None,
    min_percentile: float | None = None,
    min_minutes: float = 900,
    league_id: int | None = None,
    max_availability_score: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Multi-condition transfer candidate search.

    Combines performance data, market valuation, and contract situation
    into a single search endpoint.

    Returns candidates ranked by composite score combining:
    - Statistical performance (percentile rank)
    - Market value attractiveness (stat/market ratio)
    - Availability (contract situation)
    """
    reference_date = datetime.now(timezone.utc)

    # Start with players who have published percentile data
    query = (
        db.query(Player)
        .join(StatSnapshot, StatSnapshot.player_id == Player.id)
        .join(
            PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id
        )
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == "si_index",
            PercentileSnapshot.index_score.isnot(None),
            StatSnapshot.minutes_played >= min_minutes,
        )
    )

    if position_group:
        query = query.filter(Player.position_group == position_group)

    if league_id:
        query = query.join(Team, Player.current_team_id == Team.id)
        query = query.filter(Team.league_id == league_id)

    # Get unique players
    players = query.all()
    seen = set()
    unique_players = []
    for p in players:
        if p.id not in seen:
            seen.add(p.id)
            unique_players.append(p)

    # Apply age filters
    if min_age or max_age:
        filtered = []
        for p in unique_players:
            if p.date_of_birth is None:
                continue
            age = reference_date.year - p.date_of_birth.year
            if (reference_date.month, reference_date.day) < (
                p.date_of_birth.month,
                p.date_of_birth.day,
            ):
                age -= 1
            if min_age and age < min_age:
                continue
            if max_age and age > max_age:
                continue
            filtered.append(p)
        unique_players = filtered

    # Score each candidate
    results = []
    for player in unique_players:
        # Get stat data
        stat_snap = (
            db.query(StatSnapshot)
            .filter(StatSnapshot.player_id == player.id)
            .order_by(StatSnapshot.scrape_date.desc())
            .first()
        )
        if stat_snap is None:
            continue

        pct_row = (
            db.query(PercentileSnapshot)
            .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
            .filter(
                StatSnapshot.player_id == player.id,
                PercentileSnapshot.is_published.is_(True),
                PercentileSnapshot.metric_name == "si_index",
            )
            .order_by(StatSnapshot.scrape_date.desc())
            .first()
        )
        index_score = pct_row.index_score if pct_row else None
        if index_score is None:
            continue

        # Get market valuation
        latest_val = (
            db.query(MarketValuation)
            .filter(MarketValuation.player_id == player.id)
            .order_by(MarketValuation.valuation_date.desc())
            .first()
        )
        if latest_val is None:
            market_value = None
        else:
            market_value = latest_val.valuation_amount_eur
            if min_market_value and market_value < min_market_value:
                continue
            if max_market_value and market_value > max_market_value:
                continue

        # Get contract situation
        contract = get_contract_situation_score(
            db, player.id, reference_date=reference_date
        )
        if (
            max_availability_score
            and contract["availability_score"] > max_availability_score
        ):
            continue

        # Compute composite score
        stat_score = index_score * 0.5
        if market_value and market_value > 0:
            value_ratio = min(2.0, index_score / 50)  # normalize
            market_score = value_ratio * 25
        else:
            market_score = 25  # neutral if no market data

        availability_score = contract["availability_score"] * 0.25
        composite = stat_score + market_score + availability_score

        team = db.get(Team, player.current_team_id) if player.current_team_id else None
        league = db.get(League, team.league_id) if team else None

        age = None
        if player.date_of_birth:
            age = reference_date.year - player.date_of_birth.year
            if (reference_date.month, reference_date.day) < (
                player.date_of_birth.month,
                player.date_of_birth.day,
            ):
                age -= 1

        results.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "age": age,
                "position_group": player.position_group,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "league_slug": league.slug if league else None,
                "index_score": index_score,
                "market_value_eur": market_value,
                "market_source": latest_val.source if latest_val else None,
                "market_confidence": (
                    latest_val.confidence_level if latest_val else None
                ),
                "contract_status": contract["contract_status"],
                "contract_status_label": contract["contract_status_label"],
                "years_remaining": contract["years_remaining"],
                "availability_score": contract["availability_score"],
                "composite_score": round(composite, 1),
                "minutes_played": stat_snap.minutes_played,
            }
        )

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return {
        "total": len(results),
        "limit": limit,
        "offset": offset,
        "candidates": results[offset : offset + limit],
    }


# ---------------------------------------------------------------------------
# Transfer search presets (like Phase 8 search presets)
# ---------------------------------------------------------------------------

TRANSFER_PRESETS: list[dict[str, Any]] = [
    {
        "id": "young_talent_abroad",
        "name": "Young Talent Abroad",
        "rationale": "Players under 23 with strong statistical profiles outside the top-6 clubs — potential bargains before they explode in value.",
        "filters": {
            "max_age": 23,
            "min_percentile": 60,
        },
    },
    {
        "id": "breakout_performers",
        "name": "Breakout Performers",
        "rationale": "Players showing significant improvement — high recent percentile scores relative to their market valuation.",
        "filters": {
            "min_percentile": 70,
        },
    },
    {
        "id": "undervalued_established",
        "name": "Undervalued Established Players",
        "rationale": "Established players (24-29) performing at elite levels but valued conservatively — potential upgrades for mid-table clubs.",
        "filters": {
            "min_age": 24,
            "max_age": 29,
            "min_percentile": 75,
        },
    },
    {
        "id": "contract_bargains",
        "name": "Contract Bargains",
        "rationale": "Players with 1-2 years remaining on their contract — available at reduced fees before their market value drops.",
        "filters": {
            "max_availability_score": 70,
        },
    },
    {
        "id": "experienced_leaders",
        "name": "Experienced Leaders",
        "rationale": "Veteran players (30+) with elite statistical profiles — high availability, proven quality, mentorship value.",
        "filters": {
            "min_age": 30,
            "min_percentile": 70,
        },
    },
]
