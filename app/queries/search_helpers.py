"""Structured search helper functions."""

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
