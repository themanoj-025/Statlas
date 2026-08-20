"""League hub page aggregation (Phase 11 — Part C).

Composes existing query functions into a single payload for the league hub
page: header info, category leaderboards, emerging players, teams, and
coverage data. This is pure composition — no new raw data access.

Methodology: docs/analytics/emerging-player-methodology.md
League spec: docs/product/league-page-spec.md
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import load_registry
from app.models import League, StatSnapshot, Team

# Category leaderboard definitions (league-page-spec.md §4).
CATEGORY_LEADERBOARDS = [
    {
        "key": "top_scorers",
        "label": "Top scorers",
        "metric": "si_gls_p90",
        "position_groups": None,  # all positions
        "limit": 5,
    },
    {
        "key": "best_creators",
        "label": "Best creators",
        "metric": "si_kp_p90",
        "position_groups": ["AM", "W", "CM", "ST"],
        "limit": 5,
    },
    {
        "key": "best_progressors",
        "label": "Best progressors",
        "metric": "si_pprb_p90",
        "position_groups": None,
        "limit": 5,
    },
    {
        "key": "best_defenders",
        "label": "Best defenders",
        "metric": "si_tkl_p90",
        "position_groups": ["DM", "CB", "FB"],
        "limit": 5,
    },
]


def get_league_hub_data(
    db: Session,
    league_slug: str,
    *,
    season: str | None = None,
) -> dict[str, Any] | None:
    """Full league hub payload: header, categories, emerging, teams, coverage.

    Returns None when the league is not found.
    """
    league = db.query(League).filter_by(slug=league_slug).first()
    if league is None:
        return None

    season = season or "2025-26"
    registry = load_registry()

    # Teams in this league.
    teams = db.query(Team).filter(Team.league_id == league.id).order_by(Team.name).all()

    # Coverage data.
    from app.queries.coverage_queries import get_data_coverage

    coverage_rows = get_data_coverage(db, league_id=league.id)
    has_fbref = any(
        r["source"] == "fbref" and r["status"] == "active" for r in coverage_rows
    )
    has_understat = any(
        r["source"] == "understat" and r["status"] == "active" for r in coverage_rows
    )
    has_statsbomb = any(
        r["source"] == "statsbomb" and r["status"] == "active" for r in coverage_rows
    )

    # Latest snapshot date for this league.
    latest_snap = (
        db.query(StatSnapshot.scrape_date)
        .filter(StatSnapshot.league_id == league.id, StatSnapshot.season == season)
        .order_by(StatSnapshot.scrape_date.desc())
        .first()
    )
    latest_snapshot_date = latest_snap[0] if latest_snap else None

    # Category leaderboards (compose from existing leaderboard queries).
    from app.queries.leaderboard_queries import get_leaderboard

    category_results: list[dict[str, Any]] = []
    for cat in CATEGORY_LEADERBOARDS:
        if cat["position_groups"]:
            # For position-filtered categories, run one query per group and merge.
            all_entries: list[dict[str, Any]] = []
            for pg in cat["position_groups"]:
                entries = get_leaderboard(
                    db,
                    league_slug=league_slug,
                    position_group=pg,
                    metric=cat["metric"],
                    season=season,
                    limit=cat["limit"],
                )
                all_entries.extend(entries)
            # Re-sort merged results by value (direction-aware).
            metric_spec = registry["metrics"].get(cat["metric"])
            invert = bool(metric_spec and metric_spec["direction"] == "lower_is_better")
            all_entries.sort(key=lambda e: e["value"], reverse=not invert)
            entries = all_entries[: cat["limit"]]
        else:
            # For all-position categories, run per-position and merge.
            all_entries = []
            for pg in ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]:
                entries = get_leaderboard(
                    db,
                    league_slug=league_slug,
                    position_group=pg,
                    metric=cat["metric"],
                    season=season,
                    limit=cat["limit"],
                )
                all_entries.extend(entries)
            metric_spec = registry["metrics"].get(cat["metric"])
            invert = bool(metric_spec and metric_spec["direction"] == "lower_is_better")
            all_entries.sort(key=lambda e: e["value"], reverse=not invert)
            entries = all_entries[: cat["limit"]]

        # Enrich entries with slugs.
        from app.queries.player_queries import get_player_slug

        for entry in entries:
            if "slug" not in entry:
                entry["slug"] = get_player_slug(db, entry["player_id"])

        category_results.append(
            {
                "key": cat["key"],
                "label": cat["label"],
                "metric": cat["metric"],
                "metric_name": registry["metrics"]
                .get(cat["metric"], {})
                .get("name", cat["metric"]),
                "entries": entries,
            }
        )

    # Emerging players.
    from app.queries.emerging_queries import get_emerging_players

    emerging = get_emerging_players(db, league_id=league.id, season=season, limit=8)
    # Enrich emerging players with slugs.
    for ep in emerging:
        ep["slug"] = get_player_slug(db, ep["player_id"])

    # Player count.
    player_count = (
        db.query(StatSnapshot.player_id)
        .filter(StatSnapshot.league_id == league.id, StatSnapshot.season == season)
        .distinct()
        .count()
    )

    return {
        "slug": league.slug,
        "name": league.name,
        "country": league.country,
        "tier": league.tier,
        "tier_label": {
            "/tier_1": "Tier 1",
            "/tier_2": "Tier 2",
            "/tier_3": "Tier 3",
        }.get(league.tier, league.tier),
        "season": season,
        "team_count": len(teams),
        "player_count": player_count,
        "latest_snapshot_date": latest_snapshot_date,
        "has_fbref_coverage": has_fbref,
        "has_understat_coverage": has_understat,
        "has_statsbomb_coverage": has_statsbomb,
        "standings_available": False,  # no match-result standings data in MVP
        "categories": category_results,
        "emerging_players": emerging,
        "teams": [
            {
                "team_id": t.id,
                "name": t.name,
                "slug": _team_slug(t.name),
                "logo_url": t.logo_url,
            }
            for t in teams
        ],
        "coverage": coverage_rows,
    }


def _team_slug(name: str) -> str:
    """Team slug — same logic as slugify_name in player_queries."""
    import re

    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
