"""Emerging player queries (Phase 11 — Part B/C).

Reads precomputed emerging_player_scores (written by the weekly refresh
orchestration) and serves them to the league hub page and API.

Methodology: docs/analytics/emerging-player-methodology.md
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import EmergingPlayerScore, Player, Team


def get_emerging_players(
    db: Session,
    *,
    league_id: int,
    season: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Top emerging players in a league from the latest computed scores.

    Returns players sorted by score descending, with identity and trend
    metadata. Only scores from the most recent computation for this league
    are used.
    """
    # Find the most recent computed_date for this league.
    latest_date = (
        db.query(EmergingPlayerScore.computed_date)
        .filter(EmergingPlayerScore.league_id == league_id)
        .order_by(EmergingPlayerScore.computed_date.desc())
        .first()
    )
    if latest_date is None:
        return []

    scores = (
        db.query(EmergingPlayerScore)
        .filter(
            EmergingPlayerScore.league_id == league_id,
            EmergingPlayerScore.computed_date == latest_date[0],
        )
        .order_by(EmergingPlayerScore.score.desc())
        .limit(limit)
        .all()
    )
    if not scores:
        return []

    player_ids = [s.player_id for s in scores]
    players = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    # Get team names from the latest snapshot for each player.
    from app.models import StatSnapshot

    latest_snaps: dict[int, StatSnapshot] = {}
    snaps = (
        db.query(StatSnapshot)
        .filter(StatSnapshot.player_id.in_(player_ids))
        .order_by(StatSnapshot.scrape_date.desc(), StatSnapshot.player_id)
        .all()
    )
    for snap in snaps:
        latest_snaps.setdefault(snap.player_id, snap)

    team_ids = {s.team_id for s in latest_snaps.values() if s.team_id}
    teams = {t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()}

    results: list[dict[str, Any]] = []
    for score_row in scores:
        player = players.get(score_row.player_id)
        if player is None:
            continue
        snap = latest_snaps.get(score_row.player_id)
        team = teams.get(snap.team_id) if snap and snap.team_id else None
        factors = score_row.contributing_factors or {}

        # Determine trend direction from trend_magnitude.
        trend_mag = factors.get("trend_magnitude", 0)
        if trend_mag > 0.1:
            direction = "strong_up"
        elif trend_mag > 0.02:
            direction = "up"
        else:
            direction = "stable"

        results.append(
            {
                "player_id": score_row.player_id,
                "name": player.canonical_name,
                "position_group": player.position_group,
                "team": team.name if team else None,
                "score": score_row.score,
                "trend_direction": direction,
                "age": factors.get("age"),
                "minutes": factors.get("minutes"),
                "metrics_tracked": factors.get("metrics_tracked", 0),
                "contributing_factors": factors,
            }
        )

    return results
