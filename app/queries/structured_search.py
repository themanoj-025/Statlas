"""Phase 8 — structured search query layer.

The condition grammar and every execution rule are documented in
docs/product/query-builder-scope.md and enforced here:

- AND-only logic, max 8 conditions. `validate_query_definition` rejects
  anything else with a specific message — never a silent reinterpretation.
- The 900-minute qualification floor (registry `qualifying_minutes`) is
  ALWAYS applied, even when the query has no minutes condition.
- Missing data excludes, never guesses: a player without a published
  percentile for a percentile condition (or without the raw value for a raw
  condition) cannot satisfy it and is excluded; age conditions exclude
  players without a date of birth.
- Ownership (Phase 7 pattern): saved searches and history are per-user;
  foreign/missing ids raise SearchNotFound (HTTP 404), never a 403 that
  would leak existence.
- History retention: newest 50 per user, enforced on insert.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import effective_plan
from app.config import load_registry, load_search_presets, plan_limits
from app.models import (
    League,
    PercentileSnapshot,
    Player,
    SavedSearch,
    SearchHistory,
    StatSnapshot,
    Team,
)

MAX_CONDITIONS = 8
HISTORY_CAP = 50
VALID_TIERS = {"tier_1", "tier_2", "tier_3"}
VALID_POSITION_GROUPS = {"GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"}

PERCENTILE_OPERATORS = {"percentile_gte", "percentile_lte", "percentile_between"}
RAW_OPERATORS = {"gte", "lte", "between", "eq"}
MINUTES_METRIC = "minutes_played"

SORTABLE_BASE = {"index", "minutes", "age", "name"}


class InvalidQuery(ValueError):
    """The query definition violates the documented grammar (HTTP 400)."""


class SearchNotFound(ValueError):
    """Missing OR not owned — HTTP 404 (existence must not leak)."""


class SearchLimitExceeded(ValueError):
    """Free-tier saved-search cap reached — honest upsell message."""


# ---------------------------------------------------------------------------
# Validation / normalization
# ---------------------------------------------------------------------------


def validate_query_definition(query_definition: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a query definition; raise InvalidQuery on any
    violation of the grammar (query-builder-scope.md §1–2)."""
    if not isinstance(query_definition, dict):
        raise InvalidQuery("A query definition must be a JSON object.")

    logic = query_definition.get("condition_logic", "AND")
    if logic != "AND":
        raise InvalidQuery(
            f"condition_logic '{logic}' is not supported — v1 queries are AND-only "
            "(OR/grouped logic is a documented future enhancement)."
        )

    # position_group: a single group or a list (normalized to a list).
    position_group = query_definition.get("position_group")
    position_groups: list[str] | None = None
    if position_group is not None:
        raw = position_group if isinstance(position_group, list) else [position_group]
        if not raw:
            raise InvalidQuery(
                "position_group must be a group code or a list of group codes."
            )
        bad = [g for g in raw if g not in VALID_POSITION_GROUPS]
        if bad:
            raise InvalidQuery(
                f"unknown position group(s): {', '.join(map(str, bad))} — "
                f"valid groups: {', '.join(sorted(VALID_POSITION_GROUPS))}."
            )
        position_groups = list(dict.fromkeys(raw))

    league_tier = query_definition.get("league_tier")
    if league_tier is not None and league_tier not in VALID_TIERS:
        raise InvalidQuery(
            f"unknown league_tier '{league_tier}' — valid values: "
            f"{', '.join(sorted(VALID_TIERS))} (or omit for all tiers)."
        )

    age_max = query_definition.get("age_max")
    if age_max is not None:
        if not isinstance(age_max, (int, float)) or not (15 <= float(age_max) <= 60):
            raise InvalidQuery("age_max must be a number between 15 and 60.")

    conditions_raw = query_definition.get("conditions", [])
    if not isinstance(conditions_raw, list) or not conditions_raw:
        raise InvalidQuery("A query needs at least one condition.")
    if len(conditions_raw) > MAX_CONDITIONS:
        raise InvalidQuery(
            f"A query supports at most {MAX_CONDITIONS} conditions (you have {len(conditions_raw)})."
        )

    registry = load_registry()
    metrics = registry["metrics"]

    conditions: list[dict[str, Any]] = []
    for i, cond in enumerate(conditions_raw):
        if not isinstance(cond, dict):
            raise InvalidQuery(f"condition #{i + 1} must be an object.")
        metric = cond.get("metric")
        operator = cond.get("operator")
        value = cond.get("value")
        value_max = cond.get("value_max")

        if not isinstance(metric, str) or (
            metric not in metrics and metric != MINUTES_METRIC
        ):
            raise InvalidQuery(
                f"condition #{i + 1}: unknown metric '{metric}' — metric ids must come "
                "from the Metric Registry."
            )
        if metric == MINUTES_METRIC and operator not in RAW_OPERATORS:
            raise InvalidQuery(
                f"condition #{i + 1}: minutes_played only supports raw operators "
                f"({', '.join(sorted(RAW_OPERATORS))})."
            )
        if metric in metrics:
            valid = PERCENTILE_OPERATORS | RAW_OPERATORS
            if operator not in valid:
                raise InvalidQuery(
                    f"condition #{i + 1}: operator '{operator}' is not valid for metric "
                    f"'{metric}' — use {', '.join(sorted(valid))}."
                )
        if not isinstance(value, (int, float)) or not _finite(value):
            raise InvalidQuery(f"condition #{i + 1}: value must be a finite number.")

        is_percentile = operator in PERCENTILE_OPERATORS
        if is_percentile and not (0 <= float(value) <= 100):
            raise InvalidQuery(
                f"condition #{i + 1}: percentile values must be between 0 and 100."
            )
        if operator == "between":
            if not isinstance(value_max, (int, float)) or not _finite(value_max):
                raise InvalidQuery(
                    f"condition #{i + 1}: between needs a numeric value_max."
                )
            if value_max <= value:
                raise InvalidQuery(
                    f"condition #{i + 1}: value_max must be greater than value."
                )
            if is_percentile and not (0 <= float(value_max) <= 100):
                raise InvalidQuery(
                    f"condition #{i + 1}: percentile value_max must be between 0 and 100."
                )

        conditions.append(
            {
                "metric": metric,
                "operator": operator,
                "value": value,
                "value_max": (
                    value_max if operator in ("between", "percentile_between") else None
                ),
            }
        )

    return {
        "position_group": position_groups,
        "league_tier": league_tier,
        "age_max": float(age_max) if age_max is not None else None,
        "conditions": conditions,
        "condition_logic": "AND",
    }


def _finite(value: Any) -> bool:
    try:
        return value == value and abs(value) != float("inf")
    except TypeError:
        return False


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
) -> dict[str, Any]:
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


# ---------------------------------------------------------------------------
# Saved searches (Part B3)
# ---------------------------------------------------------------------------


def _owned_saved_search(db: Session, user_id: int, search_id: int) -> SavedSearch:
    search = (
        db.query(SavedSearch)
        .filter(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
        .first()
    )
    if search is None:
        raise SearchNotFound(f"saved search {search_id} not found")
    return search


def _saved_payload(search: SavedSearch) -> dict[str, Any]:
    return {
        "search_id": search.id,
        "name": search.name,
        "description": search.description,
        "query_definition": search.query_definition,
        "condition_count": len(search.query_definition.get("conditions", [])),
        "position_group": search.query_definition.get("position_group"),
        "league_tier": search.query_definition.get("league_tier"),
        "age_max": search.query_definition.get("age_max"),
        "created_at": search.created_at.isoformat(),
        "updated_at": search.updated_at.isoformat(),
        "last_run_at": search.last_run_at.isoformat() if search.last_run_at else None,
    }


def save_search(
    db: Session,
    user_id: int,
    name: str,
    query_definition: dict[str, Any],
    description: str | None = None,
) -> dict[str, Any]:
    """Save a validated query. Free tier is capped at `saved_searches_max`."""
    name = (name or "").strip()
    if not name:
        raise InvalidQuery("A saved search needs a name.")
    if len(name) > 128:
        raise InvalidQuery("Saved search names are limited to 128 characters.")
    qd = validate_query_definition(query_definition)

    plan = effective_plan(db, user_id)
    limits = plan_limits(plan)
    max_saved = limits.get("saved_searches_max")
    if max_saved is not None:
        current = db.query(SavedSearch).filter(SavedSearch.user_id == user_id).count()
        if current >= max_saved:
            raise SearchLimitExceeded(
                f"You've used your {plan} plan's allowance of {max_saved} saved "
                "searches. Upgrade to Pro for unlimited saved searches — your "
                "existing searches and history stay put."
            )

    search = SavedSearch(
        user_id=user_id,
        name=name,
        description=(description or "").strip() or None,
        query_definition=qd,
    )
    db.add(search)
    db.commit()
    return _saved_payload(search)


def list_saved_searches(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(SavedSearch)
        .filter(SavedSearch.user_id == user_id)
        .order_by(SavedSearch.updated_at.desc(), SavedSearch.id.desc())
        .all()
    )
    return [_saved_payload(s) for s in rows]


def run_saved_search(
    db: Session,
    user_id: int,
    search_id: int,
    **exec_kwargs: Any,
) -> dict[str, Any]:
    """Re-execute a saved search against CURRENT data (results may differ from
    when it was saved — the weekly refresh is explicit, never silently stale)."""
    search = _owned_saved_search(db, user_id, search_id)
    results = execute_structured_query(
        db, search.query_definition, user_id=user_id, **exec_kwargs
    )
    search.last_run_at = datetime.now(timezone.utc)
    search.updated_at = search.last_run_at
    db.commit()
    return {"saved": _saved_payload(search), "results": results}


def delete_saved_search(db: Session, user_id: int, search_id: int) -> None:
    search = _owned_saved_search(db, user_id, search_id)
    db.delete(search)
    db.commit()


# ---------------------------------------------------------------------------
# History (Part B3)
# ---------------------------------------------------------------------------


def _owned_history(db: Session, user_id: int, history_id: int) -> SearchHistory:
    row = (
        db.query(SearchHistory)
        .filter(SearchHistory.id == history_id, SearchHistory.user_id == user_id)
        .first()
    )
    if row is None:
        raise SearchNotFound(f"search history entry {history_id} not found")
    return row


def get_search_history(
    db: Session, user_id: int, limit: int = 20
) -> list[dict[str, Any]]:
    rows = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.executed_at.desc(), SearchHistory.id.desc())
        .limit(max(1, min(limit, HISTORY_CAP)))
        .all()
    )
    return [
        {
            "history_id": row.id,
            "query_definition": row.query_definition,
            "executed_at": row.executed_at.isoformat(),
            "result_count": row.result_count,
            "summary": summarize_query(row.query_definition),
        }
        for row in rows
    ]


def rerun_history_entry(
    db: Session,
    user_id: int,
    history_id: int,
    **exec_kwargs: Any,
) -> dict[str, Any]:
    """Re-execute a past query; the new run is logged as a NEW history entry."""
    row = _owned_history(db, user_id, history_id)
    results = execute_structured_query(
        db, row.query_definition, user_id=user_id, **exec_kwargs
    )
    return {"reran": {"history_id": history_id}, "results": results}


# ---------------------------------------------------------------------------
# Presets (Part B2 — public, not user-owned)
# ---------------------------------------------------------------------------


def list_presets() -> list[dict[str, Any]]:
    data = load_search_presets()
    presets = []
    for preset in data.get("presets", []):
        qd = validate_query_definition(preset["query_definition"])
        presets.append(
            {
                "id": preset["id"],
                "name": preset["name"],
                "rationale": preset["rationale"],
                "query_definition": qd,
            }
        )
    return presets


def summarize_query(qd: dict[str, Any]) -> str:
    """A scannable one-line summary for history/preset lists, naming the
    metrics actually filtered on ("Progressive passes per 90 ≥ 70th pct")."""
    registry = load_registry()
    metrics = registry["metrics"]

    def _label(cond: dict[str, Any]) -> str:
        metric = cond["metric"]
        name = (
            metrics.get(metric, {}).get("name", metric)
            if metric in metrics
            else "Minutes played"
        )
        op = cond["operator"]
        value = cond["value"]
        if op == "percentile_gte":
            return f"{name} ≥ {value:g}th pct"
        if op == "percentile_lte":
            return f"{name} ≤ {value:g}th pct"
        if op in ("between", "percentile_between"):
            return f"{name} {value:g}–{cond['value_max']:g}"
        if op == "eq":
            return f"{name} = {value:g}"
        if op == "gte":
            return f"{name} ≥ {value:g}"
        return f"{name} ≤ {value:g}"

    parts = []
    position_group = qd.get("position_group")
    if position_group:
        label = position_group if isinstance(position_group, list) else [position_group]
        parts.append(" + ".join(label))
    if qd.get("league_tier"):
        parts.append(
            {"tier_1": "Tier 1", "tier_2": "Tier 2", "tier_3": "Tier 3"}[
                qd["league_tier"]
            ]
        )
    if qd.get("age_max") is not None:
        parts.append(f"U{int(qd['age_max'])}")
    parts.extend(_label(cond) for cond in qd.get("conditions", []))
    return " · ".join(parts) or "Empty query"
