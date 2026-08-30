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
