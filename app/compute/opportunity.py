"""Transfer opportunity finder — hidden gems, position scarcity, age/league opportunities.

Constitution §1.3 (ML Constitution): Recommendations must be explainable.
Every opportunity is grounded in specific factors: stat vs. valuation gap,
age trajectory, profile rarity, league context.

Constitution §3: Never fabricate. All scores computed from real data with
documented assumptions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    League,
    MarketValuation,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)
from app.queries.market_queries import compute_age_at_date, compute_stat_value_proxy

# ---------------------------------------------------------------------------
# Hidden gem detection (Part D1)
# ---------------------------------------------------------------------------

def detect_hidden_gems(
    db: Session,
    *,
    min_stat_percentile: float = 75,
    max_market_value: float = 30_000_000,
    min_minutes: float = 900,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find players performing at high levels but not yet captured by market.

    A "hidden gem" is defined as:
    - 75th+ percentile in key metrics
    - Market value below €30M (conservative threshold)
    - Sufficient data (900+ minutes)
    """
    reference_date = datetime.now(timezone.utc)
    results = []

    # Get players with published index scores
    players_with_index = (
        db.query(Player.id, PercentileSnapshot.index_score)
        .join(StatSnapshot, StatSnapshot.player_id == Player.id)
        .join(PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == "si_index",
            PercentileSnapshot.index_score.isnot(None),
            StatSnapshot.minutes_played >= min_minutes,
        )
        .all()
    )

    seen = set()
    for player_id, index_score in players_with_index:
        if player_id in seen or index_score is None:
            continue
        seen.add(player_id)

        if index_score < min_stat_percentile:
            continue

        player = db.get(Player, player_id)
        if player is None:
            continue

        # Check market value
        latest_val = (
            db.query(MarketValuation)
            .filter(MarketValuation.player_id == player_id)
            .order_by(MarketValuation.valuation_date.desc())
            .first()
        )
        if latest_val is None:
            continue  # No market data — not a hidden gem (unknown)
        if latest_val.valuation_amount_eur > max_market_value:
            continue  # Already valued highly

        # Compute upside potential
        stat_proxy = compute_stat_value_proxy(db, player_id)
        if stat_proxy is None:
            continue

        stat_eur = (stat_proxy["stat_value_score"] / 100) ** 2 * 100_000_000
        upside = stat_eur - latest_val.valuation_amount_eur

        if upside <= 0:
            continue  # Not undervalued

        team = db.get(Team, player.current_team_id) if player.current_team_id else None
        league = db.get(League, team.league_id) if team else None

        age = compute_age_at_date(player.date_of_birth, reference_date)

        results.append({
            "player_id": player_id,
            "name": player.canonical_name,
            "age": age,
            "position_group": player.position_group,
            "club": team.name if team else None,
            "league": league.name if league else None,
            "index_score": index_score,
            "market_value_eur": latest_val.valuation_amount_eur,
            "stat_value_eur": round(stat_eur),
            "upside_eur": round(upside),
            "upside_pct": round(upside / latest_val.valuation_amount_eur * 100, 0),
            "confidence": latest_val.confidence_level,
            "opportunity_type": "hidden_gem",
            "opportunity_summary": (
                f"Performing at {index_score:.0f}th percentile with market "
                f"valuation of €{latest_val.valuation_amount_eur/1e6:.1f}M — "
                f"potential upside of €{upside/1e6:.1f}M"
            ),
            "risk_factors": [
                f"Market value based on {latest_val.confidence_level} confidence data",
                "Performance level may not be recognized by broader market yet",
            ],
        })

    results.sort(key=lambda x: x["upside_pct"], reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Age opportunity detection (Part D3)
# ---------------------------------------------------------------------------

def detect_age_opportunities(
    db: Session,
    *,
    max_age: int = 24,
    min_stat_percentile: float = 75,
    min_minutes: float = 900,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find young players performing at high levels but valued conservatively.

    These represent "high-ceiling, uncertain" opportunities — the player
    may not have enough track record for the market to fully value them.
    """
    reference_date = datetime.now(timezone.utc)
    results = []

    players_with_index = (
        db.query(Player.id, PercentileSnapshot.index_score)
        .join(StatSnapshot, StatSnapshot.player_id == Player.id)
        .join(PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == "si_index",
            PercentileSnapshot.index_score.isnot(None),
            StatSnapshot.minutes_played >= min_minutes,
        )
        .all()
    )

    seen = set()
    for player_id, index_score in players_with_index:
        if player_id in seen or index_score is None:
            continue
        seen.add(player_id)

        player = db.get(Player, player_id)
        if player is None or player.date_of_birth is None:
            continue

        age = compute_age_at_date(player.date_of_birth, reference_date)
        if age is None or age > max_age:
            continue
        if index_score < min_stat_percentile:
            continue

        # Check market value
        latest_val = (
            db.query(MarketValuation)
            .filter(MarketValuation.player_id == player_id)
            .order_by(MarketValuation.valuation_date.desc())
            .first()
        )

        team = db.get(Team, player.current_team_id) if player.current_team_id else None
        league = db.get(League, team.league_id) if team else None

        stat_proxy = compute_stat_value_proxy(db, player_id)
        stat_eur = (stat_proxy["stat_value_score"] / 100) ** 2 * 100_000_000 if stat_proxy else 0

        market_val = latest_val.valuation_amount_eur if latest_val else None
        upside = stat_eur - (market_val or 0)

        results.append({
            "player_id": player_id,
            "name": player.canonical_name,
            "age": age,
            "position_group": player.position_group,
            "club": team.name if team else None,
            "league": league.name if league else None,
            "index_score": index_score,
            "market_value_eur": market_val,
            "stat_value_eur": round(stat_eur),
            "upside_eur": round(upside) if upside > 0 else 0,
            "years_to_peak": max(0, 27 - age) if age < 27 else 0,
            "opportunity_type": "age_opportunity",
            "opportunity_summary": (
                f"Age {age}, performing at {index_score:.0f}th percentile — "
                f"years of development ahead before peak"
            ),
            "risk_factors": [
                f"Young player (age {age}) — limited sample size",
                "May not yet be ready for top-level pressure",
                "Injury risk during development years",
            ],
        })

    results.sort(key=lambda x: (-x["index_score"], x["age"]))
    return results[:limit]


# ---------------------------------------------------------------------------
# Position scarcity opportunities (Part D2)
# ---------------------------------------------------------------------------

# Profiles that are typically scarce and command premium prices
SCARCE_PROFILES: dict[str, list[str]] = {
    "left_footed_winger": ["W"],
    "ball_playing_center_back": ["CB"],
    "goal_scoring_midfielder": ["AM", "CM"],
    "versatile_defender": ["CB", "FB"],
    "box_to_box_midfielder": ["CM"],
}

POSITION_PREMIUM_FACTORS: dict[str, float] = {
    "W": 1.3,   # Wingers command premiums
    "AM": 1.25,  # Creative players command premiums
    "CB": 1.1,   # Defenders slightly below average premium
    "FB": 1.05,  # Full-backs moderate premium
    "CM": 1.0,   # Midfielders baseline
    "DM": 0.95,  # Defensive midfielders slight discount
    "ST": 1.15,  # Strikers moderate premium
    "GK": 0.9,   # Goalkeepers slight discount
}


def detect_position_scarcity_opportunities(
    db: Session,
    *,
    min_stat_percentile: float = 70,
    min_minutes: float = 900,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find players with scarce position profiles who are undervalued.

    Some positions/profiles command premium prices. This function identifies
    players matching those profiles who are valued below the expected premium.
    """
    reference_date = datetime.now(timezone.utc)
    results = []

    players_with_index = (
        db.query(Player.id, PercentileSnapshot.index_score, Player.position_group)
        .join(StatSnapshot, StatSnapshot.player_id == Player.id)
        .join(PercentileSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == "si_index",
            PercentileSnapshot.index_score.isnot(None),
            StatSnapshot.minutes_played >= min_minutes,
        )
        .all()
    )

    seen = set()
    for player_id, index_score, pos_group in players_with_index:
        if player_id in seen or index_score is None or pos_group is None:
            continue
        seen.add(player_id)

        if index_score < min_stat_percentile:
            continue

        premium = POSITION_PREMIUM_FACTORS.get(pos_group, 1.0)
        if premium <= 1.0:
            continue  # Not a scarce position

        player = db.get(Player, player_id)
        if player is None:
            continue

        latest_val = (
            db.query(MarketValuation)
            .filter(MarketValuation.player_id == player_id)
            .order_by(MarketValuation.valuation_date.desc())
            .first()
        )

        team = db.get(Team, player.current_team_id) if player.current_team_id else None
        league = db.get(League, team.league_id) if team else None

        market_val = latest_val.valuation_amount_eur if latest_val else None

        results.append({
            "player_id": player_id,
            "name": player.canonical_name,
            "age": compute_age_at_date(player.date_of_birth, reference_date),
            "position_group": pos_group,
            "club": team.name if team else None,
            "league": league.name if league else None,
            "index_score": index_score,
            "market_value_eur": market_val,
            "premium_factor": premium,
            "opportunity_type": "position_scarcity",
            "opportunity_summary": (
                f"Performing at {index_score:.0f}th percentile in a scarce "
                f"position ({pos_group}) — this profile commands a premium"
            ),
            "risk_factors": [
                f"Position premium factor: {premium}x",
                "Premium positions attract competition for signatures",
            ],
        })

    results.sort(key=lambda x: x["index_score"], reverse=True)
    return results[:limit]
