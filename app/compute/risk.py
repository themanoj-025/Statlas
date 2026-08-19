"""Risk and uncertainty modeling for transfer intelligence.

Constitution §1.3: Every recommendation must be explainable. Risk factors
are explicit, not hidden behind positive numbers.

Constitution §3: Never fabricate. Risk scores are computed from real data
with documented assumptions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    ArchetypeAssignment,
    ClusteringModel,
    League,
    Player,
    StatSnapshot,
    Team,
)


def compute_valuation_confidence(
    db: Session,
    player_id: int,
) -> dict[str, Any]:
    """Score how confident we can be in a player's market valuation.

    Factors:
    - Data recency: how recent is the valuation data?
    - Market presence: number of data points (reports, transactions)
    - Stat sample size: minutes played
    - Contract clarity: is contract status known?

    Returns:
    - confidence_score: 0-100
    - confidence_level: high/medium/low
    - factors: breakdown of confidence components
    """
    from app.models import MarketValuation

    # Get all valuations for this player
    valuations = (
        db.query(MarketValuation)
        .filter(MarketValuation.player_id == player_id)
        .order_by(MarketValuation.valuation_date.desc())
        .all()
    )

    reference_date = datetime.now(timezone.utc)
    factors = {}

    # Factor 1: Data recency (max 25 points)
    if valuations:
        val_date = valuations[0].valuation_date
        # Ensure both datetimes are timezone-aware for subtraction
        if val_date.tzinfo is None:
            val_date = val_date.replace(tzinfo=timezone.utc)
        days_old = (reference_date - val_date).days
        recency_score = max(0, 25 - (days_old / 30) * 2)
        factors["recency"] = {
            "score": round(recency_score, 1),
            "detail": f"Latest valuation is {days_old} days old",
        }
    else:
        recency_score = 0
        factors["recency"] = {"score": 0, "detail": "No valuation data available"}

    # Factor 2: Market presence (max 25 points)
    n_valuations = len(valuations)
    presence_score = min(25, n_valuations * 5)
    factors["market_presence"] = {
        "score": round(presence_score, 1),
        "detail": f"{n_valuations} valuation data point(s)",
    }

    # Factor 3: Stat sample size (max 25 points)
    snap = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.player_id == player_id)
        .order_by(StatSnapshot.minutes_played.desc())
        .first()
    )
    if snap and snap.minutes_played >= 2000:
        sample_score = 25
    elif snap and snap.minutes_played >= 1000:
        sample_score = 18
    elif snap:
        sample_score = 10
    else:
        sample_score = 0
    factors["sample_size"] = {
        "score": round(sample_score, 1),
        "detail": f"{snap.minutes_played:.0f} minutes" if snap else "No match data",
    }

    # Factor 4: Contract clarity (max 25 points)
    from app.models import ContractStatus
    contract = (
        db.query(ContractStatus)
        .filter(ContractStatus.player_id == player_id)
        .order_by(ContractStatus.snapshot_date.desc())
        .first()
    )
    if contract and contract.contract_end_date:
        contract_score = 25
    elif contract:
        contract_score = 15
    else:
        contract_score = 0
    factors["contract_clarity"] = {
        "score": round(contract_score, 1),
        "detail": "Contract end date known" if contract_score == 25 else "Contract status limited",
    }

    total = recency_score + presence_score + sample_score + contract_score
    if total >= 75:
        level = "high"
    elif total >= 45:
        level = "medium"
    else:
        level = "low"

    return {
        "player_id": player_id,
        "confidence_score": round(total, 1),
        "confidence_level": level,
        "factors": factors,
    }


def compute_transfer_risk(
    db: Session,
    player_id: int,
    *,
    target_league_tier: str | None = None,
    target_position_group: str | None = None,
) -> dict[str, Any]:
    """Assess the risk of transferring a player to a new context.

    Risk tiers:
    - Low risk: elite profile, proven in top leagues
    - Medium risk: strong stats, moving up in tier or changing role
    - High risk: breakout season, role change, new league, injury concerns

    Returns:
    - risk_tier: low/medium/high
    - risk_score: 0-100 (higher = riskier)
    - risk_factors: list of specific risk factors
    - mitigation_factors: list of factors that reduce risk
    """
    from app.queries.market_queries import compute_age_at_date

    player = db.get(Player, player_id)
    if player is None:
        return {"risk_tier": "unknown", "risk_score": 50, "risk_factors": ["Player not found"], "mitigation_factors": []}

    reference_date = datetime.now(timezone.utc)
    risk_factors = []
    mitigation_factors = []
    risk_score = 0

    # Factor 1: League tier transition (max 30 points)
    current_team = db.get(Team, player.current_team_id) if player.current_team_id else None
    current_league = db.get(League, current_team.league_id) if current_team else None

    if current_league and target_league_tier:
        tier_map = {"tier_1": 1, "tier_2": 2, "tier_3": 3}
        current_tier_num = tier_map.get(current_league.tier, 3)
        target_tier_num = tier_map.get(target_league_tier, 3)
        if target_tier_num < current_tier_num:
            # Moving up
            risk_score += 15
            risk_factors.append(f"Moving up in tier ({current_league.tier} → {target_league_tier})")
        elif target_tier_num == current_tier_num:
            mitigation_factors.append("Same league tier — familiar competition level")

    # Factor 2: Position change (max 25 points)
    if target_position_group and player.position_group != target_position_group:
        risk_score += 20
        risk_factors.append(f"Position change ({player.position_group} → {target_position_group})")
    else:
        mitigation_factors.append("Same position group — no role adaptation needed")

    # Factor 3: Sample size (max 25 points)
    snap = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.player_id == player_id)
        .order_by(StatSnapshot.minutes_played.desc())
        .first()
    )
    if snap:
        if snap.minutes_played < 1000:
            risk_score += 15
            risk_factors.append(f"Small sample size ({snap.minutes_played:.0f} minutes)")
        elif snap.minutes_played >= 2000:
            mitigation_factors.append(f"Extensive sample ({snap.minutes_played:.0f} minutes)")
    else:
        risk_score += 20
        risk_factors.append("No match data available")

    # Factor 4: Age (max 20 points)
    age = compute_age_at_date(player.date_of_birth, reference_date)
    if age:
        if age < 22:
            risk_score += 10
            risk_factors.append(f"Young player (age {age}) — limited adaptation experience")
            mitigation_factors.append(f"Young age ({age}) — high ceiling and adaptation potential")
        elif age > 32:
            risk_score += 5
            risk_factors.append(f"Older player (age {age}) — shorter contract horizon")
        else:
            mitigation_factors.append(f"Prime age ({age}) — proven physical peak")

    # Factor 5: Archetype transferability
    archetype_row = (
        db.query(ArchetypeAssignment)
        .join(ClusteringModel, ArchetypeAssignment.model_id == ClusteringModel.id)
        .filter(
            ArchetypeAssignment.player_id == player_id,
            ClusteringModel.status == "in_production",
        )
        .order_by(ArchetypeAssignment.snapshot_date.desc())
        .first()
    )
    if archetype_row and not archetype_row.is_outlier:
        mitigation_factors.append("Well-defined archetype — predictable playing style")
    elif archetype_row and archetype_row.is_outlier:
        risk_score += 10
        risk_factors.append("Unusual statistical profile — archetype is atypical")

    # Clamp and determine tier
    risk_score = min(100, max(0, risk_score))
    if risk_score <= 25:
        tier = "low"
    elif risk_score <= 55:
        tier = "medium"
    else:
        tier = "high"

    return {
        "player_id": player_id,
        "risk_tier": tier,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "mitigation_factors": mitigation_factors,
    }
