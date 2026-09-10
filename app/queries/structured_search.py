"""Phase 8 — structured search query layer.

The condition grammar and every execution rule are documented in
docs/product/query-builder-scope.md and enforced here.

Implementation split across:
- search_validation.py: exception classes, constants, validate_query_definition
- search_execution.py: execute_structured_query, _eval_condition, sorting
- search_saved.py: saved search CRUD, history, presets

This module is the backward-compatibility facade: existing consumers import
``from app.queries.structured_search import X`` (or use the ``ss.`` attribute
surface) and keep working. The exception classes and constants are re-exported
from search_validation (the canonical definitions) so a single class identity
is raised and caught everywhere.
"""

from __future__ import annotations

from app.queries.search_execution import execute_structured_query
from app.queries.search_saved import (
    delete_saved_search,
    get_search_history,
    list_presets,
    list_saved_searches,
    rerun_history_entry,
    run_saved_search,
    save_search,
    summarize_query,
)
from app.queries.search_validation import (
    HISTORY_CAP,
    MAX_CONDITIONS,
    MINUTES_METRIC,
    PERCENTILE_OPERATORS,
    RAW_OPERATORS,
    SORTABLE_BASE,
    VALID_POSITION_GROUPS,
    VALID_TIERS,
    InvalidQuery,
    SearchLimitExceeded,
    SearchNotFound,
    validate_query_definition,
)

__all__ = [
    "HISTORY_CAP",
    "InvalidQuery",
    "MAX_CONDITIONS",
    "MINUTES_METRIC",
    "PERCENTILE_OPERATORS",
    "RAW_OPERATORS",
    "SORTABLE_BASE",
    "SearchLimitExceeded",
    "SearchNotFound",
    "VALID_POSITION_GROUPS",
    "VALID_TIERS",
    "delete_saved_search",
    "execute_structured_query",
    "get_search_history",
    "list_presets",
    "list_saved_searches",
    "rerun_history_entry",
    "run_saved_search",
    "save_search",
    "summarize_query",
    "validate_query_definition",
]
