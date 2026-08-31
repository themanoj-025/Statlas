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

