"""Market queries — valuation comparison and undervaluation detection.

Constitution §3: Never fabricate a number. Every valuation returned here
comes from the market_valuations table or is computed from real percentile
data with documented assumptions.

Constitution §5: Every derived metric has a published methodology.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    League,
    MarketValuation,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)

# ---------------------------------------------------------------------------
# Age-adjustment factors (docs/analytics/player-valuation-age-curves.md)
# ---------------------------------------------------------------------------

# Peak age and adjustment curve per position group.
# A 21-year-old with 75th percentile stats is worth more than a 32-year-old
# with identical stats due to development potential.
AGE_CURVES: dict[str, dict[str, Any]] = {
    "ST": {"peak_age": 27, "rise_rate": 0.08, "decline_rate": 0.06},
    "AM": {"peak_age": 26, "rise_rate": 0.07, "decline_rate": 0.07},
    "W": {"peak_age": 26, "rise_rate": 0.08, "decline_rate": 0.06},
    "CM": {"peak_age": 27, "rise_rate": 0.06, "decline_rate": 0.05},
    "DM": {"peak_age": 28, "rise_rate": 0.05, "decline_rate": 0.04},
    "FB": {"peak_age": 27, "rise_rate": 0.06, "decline_rate": 0.05},
    "CB": {"peak_age": 28, "rise_rate": 0.05, "decline_rate": 0.04},
    "GK": {"peak_age": 29, "rise_rate": 0.04, "decline_rate": 0.03},
}


def compute_age_adjustment(age: int, position_group: str) -> float:
    """Compute age-adjustment multiplier for valuation comparison.

    Returns a multiplier (0.0-1.0+) that adjusts stat-based value
    based on the player's age relative to their position's peak.

    Formula:
    - Below peak: value rises by rise_rate per year toward 1.0
    - At peak: multiplier = 1.0
    - Above peak: value declines by decline_rate per year from 1.0
    """
    curve = AGE_CURVES.get(position_group, AGE_CURVES["CM"])
    peak = curve["peak_age"]
    rise = curve["rise_rate"]
    decline = curve["decline_rate"]

    if age <= peak:
        years_from_peak = peak - age
        return max(0.5, 1.0 - (years_from_peak * rise))
    else:
        years_past = age - peak
        return max(0.4, 1.0 - (years_past * decline))


def compute_age_at_date(dob: datetime | None, reference_date: datetime) -> int | None:
    """Compute age at a specific date."""
    if dob is None:
        return None
    years = reference_date.year - dob.year
    if (reference_date.month, reference_date.day) < (dob.month, dob.day):
        years -= 1
    return years


# ---------------------------------------------------------------------------
# Stat-based value proxy
# ---------------------------------------------------------------------------


def compute_stat_value_proxy(
    db: Session,
    player_id: int,
    *,
    snapshot_date: datetime | None = None,
) -> dict[str, Any] | None:
    """Compute a stat-based value proxy for a player.

    Uses published percentile scores, the Statlas Index, and age adjustment
    to produce a comparable "statistical performance rank" that can be
    compared against market valuation.

    Returns dict with:
    - stat_percentile: average percentile across published metrics
    - index_score: the player's Statlas Index (if available)
    - archetype_id: cluster assignment (if available)
    - age_adjustment: age-based multiplier
    - stat_value_score: combined score (0-100)
    - factors: breakdown of how the score was computed
    """
    player = db.get(Player, player_id)
    if player is None:
        return None

    # Get latest published percentiles
    query = (
        db.query(PercentileSnapshot, StatSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            StatSnapshot.player_id == player_id,
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name != "si_index",
        )
    )
    if snapshot_date is not None:
        query = query.filter(StatSnapshot.scrape_date == snapshot_date)

    rows = query.order_by(StatSnapshot.scrape_date.desc()).all()
    if not rows:
        return None

    # Get latest scrape's percentiles
    latest_scrape = rows[0][1].scrape_date
    latest_rows = [r for r in rows if r[1].scrape_date == latest_scrape]

    percentiles = {}
    for pct, _snap in latest_rows:
        if pct.percentile_value is not None:
            percentiles[pct.metric_name] = pct.percentile_value

    if not percentiles:
        return None

    avg_percentile = sum(percentiles.values()) / len(percentiles)

    # Get index score
    index_row = (
        db.query(PercentileSnapshot)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .filter(
            StatSnapshot.player_id == player_id,
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name == "si_index",
        )
        .order_by(StatSnapshot.scrape_date.desc())
        .first()
    )
    index_score = index_row.index_score if index_row else None

    # Age adjustment
    age = compute_age_at_date(player.date_of_birth, latest_scrape)
    age_adj = compute_age_adjustment(age, player.position_group) if age else 0.7

    # Combined stat value score
    stat_score = (avg_percentile * 0.6 + (index_score or 50) * 0.4) * age_adj

    return {
        "player_id": player_id,
        "stat_percentile": round(avg_percentile, 1),
        "index_score": index_score,
        "age": age,
        "age_adjustment": round(age_adj, 3),
        "stat_value_score": round(min(100, max(0, stat_score)), 1),
        "n_metrics": len(percentiles),
        "snapshot_date": latest_scrape.isoformat(),
        "factors": {
            "avg_percentile": round(avg_percentile, 1),
            "index_score": index_score,
            "age_at_snapshot": age,
            "age_multiplier": round(age_adj, 3),
            "formula": "stat_value = (avg_pct * 0.6 + index * 0.4) * age_adj",
        },
    }


# ---------------------------------------------------------------------------
# Market valuation lookup
# ---------------------------------------------------------------------------


def get_latest_valuation(
    db: Session,
    player_id: int,
    *,
    source: str | None = None,
) -> dict[str, Any] | None:
    """Get the latest market valuation for a player."""
    query = db.query(MarketValuation).filter(MarketValuation.player_id == player_id)
    if source:
        query = query.filter(MarketValuation.source == source)

    latest = query.order_by(MarketValuation.valuation_date.desc()).first()
    if latest is None:
        return None

    return {
        "player_id": player_id,
        "source": latest.source,
        "valuation_amount_eur": latest.valuation_amount_eur,
        "valuation_date": latest.valuation_date.isoformat(),
        "low_range": latest.low_range,
        "high_range": latest.high_range,
        "confidence_level": latest.confidence_level,
    }


# ---------------------------------------------------------------------------
# Valuation comparison
# ---------------------------------------------------------------------------


def get_valuation_comparison(
    db: Session,
    player_id: int,
) -> dict[str, Any] | None:
    """Compare a player's stat-based value against their market valuation.

    This is the core of the valuation comparison framework: a transparent,
    deterministic function that explains WHY a player might be undervalued
    or overvalued.

    Returns:
    - stat_value: stat-based performance score (0-100)
    - market_value: current market valuation in EUR
    - valuation_gap: difference between stat-based and market value
    - signal_strength: confidence in the comparison
    - explanation: human-readable explanation
    """
    stat = compute_stat_value_proxy(db, player_id)
    market = get_latest_valuation(db, player_id)

    if stat is None or market is None:
        return None

    player = db.get(Player, player_id)
    if player is None:
        return None

    # Convert stat score (0-100) to approximate EUR value
    # This is a rough mapping: 100th percentile ≈ €100M, 50th ≈ €20M
    # The exact mapping is documented in the methodology
    stat_eur = (stat["stat_value_score"] / 100) ** 2 * 100_000_000

    market_val = market["valuation_amount_eur"]
    gap = stat_eur - market_val
    gap_pct = (gap / market_val * 100) if market_val > 0 else 0

    # Signal strength based on data quality
    n_metrics = stat["n_metrics"]
    confidence = market["confidence_level"]
    if n_metrics >= 10 and confidence == "high":
        signal = "strong"
    elif n_metrics >= 6 and confidence != "low":
        signal = "moderate"
    else:
        signal = "weak"

    # Explanation
    if gap > 0:
        label = "potentially undervalued"
        explanation = (
            f"{player.canonical_name} ranks {stat['stat_percentile']:.0f}th percentile "
            f"statistically (Index: {stat['index_score']:.1f}), "
            f"but market estimates €{market_val/1e6:.1f}M "
            f"(source: {market['source']}). "
            f"Stat-based estimate: €{stat_eur/1e6:.1f}M — "
            f"potential undervaluation of €{abs(gap)/1e6:.1f}M "
            f"({abs(gap_pct):.0f}%)"
        )
    else:
        label = "potentially overvalued"
        explanation = (
            f"{player.canonical_name} ranks {stat['stat_percentile']:.0f}th percentile "
            f"statistically (Index: {stat['index_score']:.1f}), "
            f"but market estimates €{market_val/1e6:.1f}M "
            f"(source: {market['source']}). "
            f"Stat-based estimate: €{stat_eur/1e6:.1f}M — "
            f"potential overvaluation of €{abs(gap)/1e6:.1f}M "
            f"({abs(gap_pct):.0f}%)"
        )

    return {
        "player_id": player_id,
        "player_name": player.canonical_name,
        "stat_value_score": stat["stat_value_score"],
        "stat_value_eur": round(stat_eur),
        "market_value_eur": market_val,
        "market_source": market["source"],
        "market_confidence": market["confidence_level"],
        "valuation_gap_eur": round(gap),
        "valuation_gap_pct": round(gap_pct, 1),
        "label": label,
        "signal_strength": signal,
        "explanation": explanation,
        "age_adjustment": stat["age_adjustment"],
        "stat_snapshot_date": stat["snapshot_date"],
    }


# ---------------------------------------------------------------------------
# Undervaluation / overvaluation detection
# ---------------------------------------------------------------------------


def get_undervalued_players(
    db: Session,
    *,
    league_id: int | None = None,
    position_group: str | None = None,
    threshold: float = 0.2,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find players where stat-based value exceeds market value by threshold.

    Args:
        threshold: minimum undervaluation ratio (stat/market - 1) to include.
                   0.2 means stat-based value is 20%+ above market value.
    """
    # Get all players with both stat data and market valuations
    from sqlalchemy import and_

    # Subquery: players with latest market valuation
    latest_val = (
        db.query(
            MarketValuation.player_id,
            func.max(MarketValuation.valuation_date).label("max_date"),
        )
        .group_by(MarketValuation.player_id)
        .subquery()
    )

    valuations = (
        db.query(MarketValuation)
        .join(
            latest_val,
            and_(
                MarketValuation.player_id == latest_val.c.player_id,
                MarketValuation.valuation_date == latest_val.c.max_date,
            ),
        )
        .all()
    )

    # Batch-load players and teams (eliminates N+1).
    player_ids = [val.player_id for val in valuations]
    players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()} if player_ids else {}
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()} if team_ids else {}
    league_ids = {t.league_id for t in teams_map.values() if t.league_id}
    leagues_map = {lg.id: lg for lg in db.query(League).filter(League.id.in_(league_ids)).all()} if league_ids else {}

    results = []
    for val in valuations:
        player = players_map.get(val.player_id)
        if player is None:
            continue

        stat = compute_stat_value_proxy(db, val.player_id)
        if stat is None:
            continue

        # Apply filters
        if league_id:
            team = teams_map.get(player.current_team_id) if player.current_team_id else None
            if team is None or team.league_id != league_id:
                continue
        if position_group and player.position_group != position_group:
            continue

        # Compute gap
        stat_eur = (stat["stat_value_score"] / 100) ** 2 * 100_000_000
        market_val = val.valuation_amount_eur
        if market_val <= 0:
            continue

        gap_ratio = (stat_eur - market_val) / market_val
        if gap_ratio < threshold:
            continue

        team = teams_map.get(player.current_team_id) if player.current_team_id else None
        league = leagues_map.get(team.league_id) if team else None

        results.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": player.position_group,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "stat_value_score": stat["stat_value_score"],
                "stat_value_eur": round(stat_eur),
                "market_value_eur": market_val,
                "market_source": val.source,
                "valuation_gap_eur": round(stat_eur - market_val),
                "valuation_gap_pct": round(gap_ratio * 100, 1),
                "age": stat["age"],
                "signal_strength": "moderate" if stat["n_metrics"] >= 6 else "weak",
            }
        )

    results.sort(key=lambda x: x["valuation_gap_pct"], reverse=True)
    return results[:limit]


def get_overvalued_players(
    db: Session,
    *,
    league_id: int | None = None,
    position_group: str | None = None,
    threshold: float = 0.2,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find players where market value exceeds stat-based value by threshold.

    Overvaluation can be legitimate (young potential, scarcity premium).
    """
    from sqlalchemy import and_

    latest_val = (
        db.query(
            MarketValuation.player_id,
            func.max(MarketValuation.valuation_date).label("max_date"),
        )
        .group_by(MarketValuation.player_id)
        .subquery()
    )

    valuations = (
        db.query(MarketValuation)
        .join(
            latest_val,
            and_(
                MarketValuation.player_id == latest_val.c.player_id,
                MarketValuation.valuation_date == latest_val.c.max_date,
            ),
        )
        .all()
    )

    # Batch-load players and teams (eliminates N+1).
    player_ids = [val.player_id for val in valuations]
    players_map = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()} if player_ids else {}
    team_ids = {p.current_team_id for p in players_map.values() if p.current_team_id}
    teams_map = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()} if team_ids else {}
    league_ids = {t.league_id for t in teams_map.values() if t.league_id}
    leagues_map = {lg.id: lg for lg in db.query(League).filter(League.id.in_(league_ids)).all()} if league_ids else {}

    results = []
    for val in valuations:
        player = players_map.get(val.player_id)
        if player is None:
            continue

        stat = compute_stat_value_proxy(db, val.player_id)
        if stat is None:
            continue

        if league_id:
            team = teams_map.get(player.current_team_id) if player.current_team_id else None
            if team is None or team.league_id != league_id:
                continue
        if position_group and player.position_group != position_group:
            continue

        stat_eur = (stat["stat_value_score"] / 100) ** 2 * 100_000_000
        market_val = val.valuation_amount_eur
        if market_val <= 0 or stat_eur <= 0:
            continue

        gap_ratio = (market_val - stat_eur) / stat_eur  # positive = overvalued
        if gap_ratio < threshold:
            continue

        team = teams_map.get(player.current_team_id) if player.current_team_id else None
        league = leagues_map.get(team.league_id) if team else None

        results.append(
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": player.position_group,
                "club": team.name if team else None,
                "league": league.name if league else None,
                "stat_value_score": stat["stat_value_score"],
                "stat_value_eur": round(stat_eur),
                "market_value_eur": market_val,
                "market_source": val.source,
                "valuation_gap_eur": round(market_val - stat_eur),
                "valuation_gap_pct": round(gap_ratio * 100, 1),
                "age": stat["age"],
                "signal_strength": "moderate" if stat["n_metrics"] >= 6 else "weak",
                "note": "Overvaluation can be legitimate (young potential, scarcity, celebrity factor)",
            }
        )

    results.sort(key=lambda x: x["valuation_gap_pct"], reverse=True)
    return results[:limit]
