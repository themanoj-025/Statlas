"""Structured search — saved searches, history, and presets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth import effective_plan
from app.config import load_search_presets, plan_limits
from app.models import SavedSearch, SearchHistory
from app.queries.structured_search import (
    HISTORY_CAP,
    InvalidQuery,
    SearchLimitExceeded,
    SearchNotFound,
    validate_query_definition,
)

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
