"""Shared base class and enum definitions for all ORM models.

Every domain module imports Base and the enums it needs from here.
This avoids duplication and ensures enum names are globally unique.
"""
from __future__ import annotations

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums (native_enum=True — PostgreSQL gets real types, SQLite falls back)
# ---------------------------------------------------------------------------

SOURCE_ENUM = Enum("fbref", "understat", "statsbomb", "api_football", name="source")
POSITION_GROUP_ENUM = Enum(
    "GK", "CB", "FB", "DM", "CM", "AM", "W", "ST", name="position_group"
)
SNAPSHOT_STATUS_ENUM = Enum(
    "ingested", "flagged", "published", "failed", name="snapshot_status"
)
COVERAGE_STATUS_ENUM = Enum("active", "stale", "failed", name="coverage_status")
TIER_ENUM = Enum("tier_1", "tier_2", "tier_3", name="league_tier")
QUEUE_STATUS_ENUM = Enum("pending", "resolved", "ignored", name="queue_status")

# Phase 15 — Transfer Intelligence & Market Data
MARKET_SOURCE_ENUM = Enum(
    "transfermarkt", "understat_transfer", "instat", "manual", name="market_source"
)
TRANSFER_TYPE_ENUM = Enum("permanent", "loan", "free_agent", name="transfer_type")
TRANSFER_STATUS_ENUM = Enum("confirmed", "reported", name="transfer_status")
CONTRACT_STATUS_ENUM = Enum(
    "active", "expiring_next_season", "expired", "on_loan", name="contract_status"
)
VALUATION_CONFIDENCE_ENUM = Enum("high", "medium", "low", name="valuation_confidence")
RISK_TIER_ENUM = Enum("low", "medium", "high", name="risk_tier")

# Phase 4 — Billing / Subscriptions
SUBSCRIPTION_STATUS_ENUM = Enum(
    "active", "trialing", "past_due", "canceled", "incomplete",
    name="subscription_status",
)
PLAN_ENUM = Enum("free", "pro", "api_business", name="plan")
ACCOUNT_STATUS_ENUM = Enum("active", "suspended", "pending_deletion", name="account_status")

# Phase 7 — Scouting workspace pipeline
ENTRY_STATUS_ENUM = Enum(
    "discovered", "monitoring", "scouted", "shortlisted", "reviewed",
    "rejected", "signed", name="entry_status",
)
ENTRY_PRIORITY_ENUM = Enum("low", "medium", "high", name="entry_priority")

# Phase 10 — Watchlist & alerts
ENTITY_TYPE_ENUM = Enum("player", "team", name="entity_type")
ALERT_TYPE_ENUM = Enum(
    "percentile_movement", "club_change", "new_season_data",
    "data_coverage_change", name="alert_type",
)
DIGEST_FREQUENCY_ENUM = Enum("immediate", "daily_digest", "weekly_digest", name="digest_frequency")

# Phase 13 — Activity tracking
ENTITY_TYPE_ENUM_13 = Enum(
    "player", "team", "search", "shortlist", "report", "watch",
    name="entity_type_13",
)
ACTION_TYPE_ENUM = Enum("viewed", "created", "edited", "deleted", "shared", "run", name="action_type")

# Phase 14 — ML clustering
CLUSTERING_STATUS_ENUM = Enum("candidate", "in_production", "archived", name="clustering_status")

# Phase 16 — Organizations / RBAC
ORG_ROLE_ENUM = Enum("owner", "manager", "scout", "viewer", name="org_role")
VISIBILITY_ENUM = Enum("personal", "org_members", "restricted", name="resource_visibility")
ORG_TIER_ENUM = Enum("free", "pro", "enterprise", name="org_tier")
ORG_INVITE_STATUS_ENUM = Enum("pending", "accepted", "expired", name="org_invite_status")
AUDIT_ACTION_ENUM = Enum(
    "user_added", "user_removed", "role_changed", "resource_created",
    "resource_shared", "resource_deleted", "comment_added", name="audit_action",
)
MENTION_STATUS_ENUM = Enum("pending", "read", name="mention_status")
