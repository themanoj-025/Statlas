"""Structured search — execution layer."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import effective_plan
from app.config import load_registry, plan_limits
from app.models import (
    League,
    PercentileSnapshot,
    Player,
    StatSnapshot,
    Team,
)
from app.queries.structured_search import (
    MINUTES_METRIC,
    PERCENTILE_OPERATORS,
    RAW_OPERATORS,
    SORTABLE_BASE,
    VALID_POSITION_GROUPS,
    InvalidQuery,
    _finite,
    validate_query_definition,
)

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _age_at(dob: date | None, ref: datetime) -> int | None:
    """Full years between date of birth and the reference snapshot date."""
    if dob is None or ref is None:
        return None
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def _team_name(db: Session, team_id: int | None) -> str | None:
    if team_id is None:
        return None
    team = db.get(Team, team_id)
    return team.name if team else None


def _eval_condition(cond: dict[str, Any], value: Any) -> bool:
    """Evaluate one condition against an actual value. A missing value (None)
    never passes — exclusion by design (query-builder-scope.md §3.2)."""
    if value is None:
        return False
    operator = cond["operator"]
    threshold = cond["value"]
    if operator == "percentile_gte" or operator == "gte":
        return value >= threshold
    if operator == "percentile_lte" or operator == "lte":
        return value <= threshold
    if operator == "eq":
        return value == threshold
    if operator == "between" or operator == "percentile_between":
        return cond["value_max"] >= value >= threshold
    return False


def execute_structured_query(
    db: Session,
    query_definition: dict[str, Any],
    *,
    user_id: int | None = None,
    log_history: bool = True,
    limit: int = 25,
    offset: int = 0,
    sort_by: str = "index",
    sort_dir: str | None = None,
    season: str | None = None,
) -> dict[str, Any] -> None:
    """Execute a structured query against the published population.

    Returns a paginated result set where every entry carries the actual values
    behind each condition (`condition_values`) — the "why each result matched"
    transparency requirement (Part B1).
    """
    qd = validate_query_definition(query_definition)
    registry = load_registry()
    qualifying_minutes = registry["qualifying_minutes"]
    index_id = registry["index_metric_id"]
    metrics = registry["metrics"]

    # The current data set: latest season, latest snapshot date in it.
    if season is None:
        season = db.query(func.max(StatSnapshot.season)).scalar()
    if not season:
        raise InvalidQuery("No season data exists yet.")
    latest_date = (
        db.query(func.max(StatSnapshot.scrape_date))
        .filter(StatSnapshot.season == season)
        .scalar()
    )
    if latest_date is None:
        raise InvalidQuery(f"No snapshot data for season '{season}'.")

    # Metrics needed: the index row (defines the published population) +
    # every percentile-condition metric + the sort metric if it is a registry
    # metric not already covered.
    needed = {index_id}
    for cond in qd["conditions"]:
        if cond["operator"] in PERCENTILE_OPERATORS:
            needed.add(cond["metric"])
    if sort_by in metrics:
        needed.add(sort_by)

    rows = (
        db.query(PercentileSnapshot, StatSnapshot, Player, League)
        .join(StatSnapshot, PercentileSnapshot.stat_snapshot_id == StatSnapshot.id)
        .join(Player, StatSnapshot.player_id == Player.id)
        .join(League, StatSnapshot.league_id == League.id)
        .filter(
            PercentileSnapshot.is_published.is_(True),
            PercentileSnapshot.metric_name.in_(needed),
            StatSnapshot.scrape_date == latest_date,
            StatSnapshot.season == season,
        )
        .all()
    )

    # Assemble per-player data (at most one row per (player, metric) at the
    # latest date — the percentile unique key includes the snapshot).
    players: dict[int, dict[str, Any]] = {}
    for percentile, snap, player, league in rows:
        entry = players.setdefault(
            player.id,
            {
                "player_id": player.id,
                "name": player.canonical_name,
                "position_group": percentile.position_group,
                "club": _team_name(db, snap.team_id),
                "league": league.name,
                "league_slug": league.slug,
                "tier": league.tier,
                "minutes": snap.minutes_played,
                "matches": snap.matches_played,
                "age": _age_at(player.date_of_birth, snap.scrape_date),
                "dob_missing": player.date_of_birth is None,
                "raw_stats": snap.raw_stats or {},
                "snapshot_date": snap.scrape_date,
                "percentiles": {},
                "index": None,
            },
        )
        if percentile.metric_name == index_id:
            entry["index"] = percentile.index_score
        else:
            entry["percentiles"][percentile.metric_name] = percentile.percentile_value

    def _condition_actual(entry: dict[str, Any], cond: dict[str, Any]) -> Any:
        metric = cond["metric"]
        if metric == MINUTES_METRIC:
            return entry["minutes"]
        if cond["operator"] in PERCENTILE_OPERATORS:
            return entry["percentiles"].get(metric)
        return entry["raw_stats"].get(metric)

    # The always-applied qualification floor + scalar filters. Condition pass
    # counts are computed over this filtered population for diagnostics.
    candidates: list[dict[str, Any]] = []
    for entry in players.values():
        if entry["minutes"] < qualifying_minutes:
            continue
        if qd["position_group"] and entry["position_group"] not in qd["position_group"]:
            continue
        if qd["league_tier"] and entry["tier"] != qd["league_tier"]:
            continue
        if qd["age_max"] is not None:
            if entry["dob_missing"] or entry["age"] is None:
                continue  # cannot verify age -> excluded (missing data rule)
            if entry["age"] > qd["age_max"]:
                continue
        entry["condition_values"] = [
            {
                "metric": cond["metric"],
                "operator": cond["operator"],
                "value": cond["value"],
                "value_max": cond["value_max"],
                "actual": _condition_actual(entry, cond),
            }
            for cond in qd["conditions"]
        ]
        candidates.append(entry)

    # Per-condition individual pass counts (over the floor+scalar population)
    # — used for the "most restrictive condition" empty-result guidance.
    per_condition_counts = []
    for cond in qd["conditions"]:
        passing = sum(
            1
            for entry in candidates
            if _eval_condition(cond, _condition_actual(entry, cond))
        )
        per_condition_counts.append(
            {
                "metric": cond["metric"],
                "metric_name": metrics.get(cond["metric"], {}).get(
                    "name", cond["metric"]
                ),
                "operator": cond["operator"],
                "value": cond["value"],
                "value_max": cond["value_max"],
                "passing_count": passing,
            }
        )

    survivors = [
        entry
        for entry in candidates
        if all(
            _eval_condition(cond, entry["condition_values"][i]["actual"])
            for i, cond in enumerate(qd["conditions"])
        )
    ]

    # Sorting — direction-aware for registry metrics (mirrors leaderboard).
    if sort_by == "name":
        survivors.sort(
            key=lambda e: e["name"].lower(), reverse=(sort_dir or "asc") == "desc"
        )
    elif sort_by == "minutes":
        survivors.sort(
            key=lambda e: e["minutes"], reverse=(sort_dir or "desc") == "desc"
        )
    elif sort_by == "age":
        survivors.sort(
            key=lambda e: e["age"] or 0, reverse=(sort_dir or "desc") == "desc"
        )
    elif sort_by in metrics:
        spec = metrics[sort_by]
        default_desc = spec["direction"] != "lower_is_better"
        if sort_dir is not None:
            survivors.sort(
                key=lambda e: (e["percentiles"].get(sort_by) if spec else None) or 0,
                reverse=sort_dir == "desc",
            )
        else:
            survivors.sort(
                key=lambda e: (e["percentiles"].get(sort_by)) or 0,
                reverse=default_desc,
            )
    else:  # index (default)
        survivors.sort(
            key=lambda e: e["index"] if e["index"] is not None else -1,
            reverse=(sort_dir or "desc") == "desc",
        )

    total = len(survivors)
    page = survivors[offset : offset + limit]

    from app.queries.player_queries import player_slug_map

    slugs = {p["player_id"]: p["slug"] for p in player_slug_map(db)}
    entries = []
    for entry in page:
        condition_values = []
        for cond, cv in zip(qd["conditions"], entry["condition_values"]):
            metric_spec = metrics.get(cond["metric"])
            condition_values.append(
                {
                    **cv,
                    "metric_name": (metric_spec or {}).get("name", cond["metric"]),
                    "condition_type": (
                        "percentile"
                        if cond["operator"] in PERCENTILE_OPERATORS
                        else "raw"
                    ),
                }
            )
        entries.append(
            {
                "player_id": entry["player_id"],
                "name": entry["name"],
                "slug": slugs.get(entry["player_id"]),
                "position_group": entry["position_group"],
                "club": entry["club"],
                "league": entry["league"],
                "league_slug": entry["league_slug"],
                "tier": entry["tier"],
                "minutes": entry["minutes"],
                "matches": entry["matches"],
                "age": entry["age"],
                "index": entry["index"],
                "snapshot_date": entry["snapshot_date"].isoformat(),
                "condition_values": condition_values,
            }
        )

    most_restrictive = None
    if per_condition_counts:
        most_restrictive = min(per_condition_counts, key=lambda c: c["passing_count"])

    result = {
        "query": qd,
        "season": season,
        "snapshot_date": latest_date.isoformat(),
        "qualifying_minutes": qualifying_minutes,
        "note": (
            "Results reflect only published players with complete data for every "
            "selected metric; every result has at least "
            f"{qualifying_minutes} league minutes (the qualification floor)."
        ),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "entries": entries,
        "diagnostics": (
            {
                "per_condition_counts": per_condition_counts,
                "most_restrictive": most_restrictive,
            }
            if total == 0
            else None
        ),
    }

    if user_id is not None and log_history:
        _log_history(db, user_id, qd, total)

    return result


def _log_history(
    db: Session, user_id: int, qd: dict[str, Any], result_count: int
) -> None:
    db.add(
        SearchHistory(
            user_id=user_id,
            query_definition=qd,
            result_count=result_count,
        )
    )
    db.commit()
    # Retention cap: newest HISTORY_CAP per user (documented, bounded).
    stale = (
        db.query(SearchHistory.id)
        .filter(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.executed_at.desc(), SearchHistory.id.desc())
        .offset(HISTORY_CAP)
        .all()
    )
    if stale:
        db.query(SearchHistory).filter(
            SearchHistory.id.in_([row[0] for row in stale])
        ).delete(synchronize_session=False)
    db.commit()

