"""Phase 8 — structured search query layer.

The condition grammar and every execution rule are documented in
docs/product/query-builder-scope.md and enforced here.

Implementation split across:
- search_validation.py: exception classes, validate_query_definition, helpers
- search_execution.py: execute_structured_query, _eval_condition, sorting
- search_saved.py: saved search CRUD, history, presets
"""

from __future__ import annotations

from typing import Any

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


def _finite(value: Any) -> bool:
    try:
        return value == value and abs(value) != float("inf")
    except TypeError:
        return False


# Re-export from split modules
from app.queries.search_validation import validate_query_definition  # noqa: F401, E402
from app.queries.search_execution import execute_structured_query  # noqa: F401, E402
from app.queries.search_saved import (  # noqa: F401, E402
    save_search,
    list_saved_searches,
    run_saved_search,
    delete_saved_search,
    get_search_history,
    rerun_history_entry,
    list_presets,
    summarize_query,
)
