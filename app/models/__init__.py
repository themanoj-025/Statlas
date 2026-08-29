"""ORM models — backward-compatible re-exports.

This package replaces the former monolithic ``app/models.py``.  Every domain
module defines its models in isolation; this ``__init__.py`` re-exports them
all so that existing ``from app.models import User`` (etc.) imports keep
working without changes.

Import order matters: ``base`` first (defines ``Base`` and all enums),
then domain modules (they reference ``Base`` and cross-reference each other
via string-based ``relationship()`` calls).
"""

from __future__ import annotations

# 10. Analytics domain
from app.models.analytics import (
    AnalyticsAccessLog,
    AnalyticsAlert,
    AnalyticsEvent,
    AnalyticsSession,
    CohortRetention,
    DailyMetric,
    FeatureUsage,
)

# 1. Base class + all enums (must be first)
from app.models.base import (
    ACCOUNT_STATUS_ENUM,
    ACTION_TYPE_ENUM,
    ALERT_TYPE_ENUM,
    AUDIT_ACTION_ENUM,
    CLUSTERING_STATUS_ENUM,
    CONTRACT_STATUS_ENUM,
    COVERAGE_STATUS_ENUM,
    DIGEST_FREQUENCY_ENUM,
    ENTITY_TYPE_ENUM,
    ENTITY_TYPE_ENUM_13,
    ENTRY_PRIORITY_ENUM,
    ENTRY_STATUS_ENUM,
    MARKET_SOURCE_ENUM,
    MENTION_STATUS_ENUM,
    ORG_INVITE_STATUS_ENUM,
    ORG_ROLE_ENUM,
    ORG_TIER_ENUM,
    PLAN_ENUM,
    POSITION_GROUP_ENUM,
    QUEUE_STATUS_ENUM,
    RISK_TIER_ENUM,
    SNAPSHOT_STATUS_ENUM,
    SOURCE_ENUM,
    SUBSCRIPTION_STATUS_ENUM,
    TIER_ENUM,
    TRANSFER_STATUS_ENUM,
    TRANSFER_TYPE_ENUM,
    VALUATION_CONFIDENCE_ENUM,
    VISIBILITY_ENUM,
    Base,
)

# 11. Clustering domain (ML archetypes)
from app.models.clustering import (
    ArchetypeAssignment,
    ArchetypeDefinition,
    ClusteringModel,
    ClusteringMonitoringLog,
)

# 9. Dashboard domain
from app.models.dashboard import (
    ActivityLog,
    DashboardState,
    SavedPlayer,
)

# 13. Organization domain (RBAC, audit, comments)
from app.models.org import (
    AuditLog,
    Comment,
    Mention,
    Organization,
    OrgInvite,
    OrgMembership,
    OrgSettings,
)

# 2. Player domain (League, Team, Player, aliases, fixtures, emerging)
from app.models.player import (
    EmergingPlayerScore,
    Fixture,
    League,
    Player,
    PlayerNameAlias,
    Team,
)

# 7. Report domain
from app.models.report import (
    Report,
    ReportQuota,
)

# 6. Search domain
from app.models.search import (
    SavedSearch,
    SearchHistory,
)

# 3. Stats domain (snapshots, percentiles, events, coverage, anomalies)
from app.models.stats import (
    DataCoverage,
    IngestionAnomaly,
    MatchEvent,
    PercentileSnapshot,
    ReconciliationQueue,
    StatSnapshot,
)

# 14. Tactical domain
from app.models.tactical import (
    MatchFormation,
    MatchPassingNetwork,
    MatchSpatialAnalysis,
)

# 12. Transfer domain
from app.models.transfer import (
    ContractStatus,
    MarketValuation,
    TransferHistory,
)

# 4. User domain (accounts, sessions, subscriptions, API keys, quotas)
from app.models.user import (
    ApiKey,
    AssistantQuota,
    EmailVerificationToken,
    PasswordResetToken,
    SessionToken,
    Subscription,
    User,
    WebhookEvent,
)

# 8. Watch domain
from app.models.watch import (
    NotificationPreferences,
    Watch,
    WatchAlert,
)

# 5. Workspace domain (shortlists, entries, notes, tags, status history)
from app.models.workspace import (
    EntryNote,
    EntryTag,
    Shortlist,
    ShortlistEntry,
    StatusHistory,
)

__all__ = [
    # Base
    "Base",
    # Enums
    "ACCOUNT_STATUS_ENUM", "ACTION_TYPE_ENUM", "ALERT_TYPE_ENUM",
    "AUDIT_ACTION_ENUM", "CLUSTERING_STATUS_ENUM", "COVERAGE_STATUS_ENUM",
    "CONTRACT_STATUS_ENUM", "DIGEST_FREQUENCY_ENUM", "ENTITY_TYPE_ENUM",
    "ENTITY_TYPE_ENUM_13", "ENTRY_PRIORITY_ENUM", "ENTRY_STATUS_ENUM",
    "MARKET_SOURCE_ENUM", "MENTION_STATUS_ENUM", "ORG_INVITE_STATUS_ENUM",
    "ORG_ROLE_ENUM", "ORG_TIER_ENUM", "PLAN_ENUM", "POSITION_GROUP_ENUM",
    "QUEUE_STATUS_ENUM", "RISK_TIER_ENUM", "SNAPSHOT_STATUS_ENUM",
    "SOURCE_ENUM", "SUBSCRIPTION_STATUS_ENUM", "TIER_ENUM",
    "TRANSFER_STATUS_ENUM", "TRANSFER_TYPE_ENUM", "VALUATION_CONFIDENCE_ENUM",
    "VISIBILITY_ENUM",
    # Player
    "League", "Team", "Player", "PlayerNameAlias", "Fixture",
    "EmergingPlayerScore",
    # Stats
    "StatSnapshot", "PercentileSnapshot", "MatchEvent", "DataCoverage",
    "IngestionAnomaly", "ReconciliationQueue",
    # User
    "User", "SessionToken", "PasswordResetToken", "EmailVerificationToken",
    "Subscription", "ApiKey", "WebhookEvent", "AssistantQuota",
    # Workspace
    "Shortlist", "ShortlistEntry", "EntryNote", "EntryTag", "StatusHistory",
    # Search
    "SavedSearch", "SearchHistory",
    # Report
    "Report", "ReportQuota",
    # Watch
    "Watch", "WatchAlert", "NotificationPreferences",
    # Dashboard
    "ActivityLog", "DashboardState", "SavedPlayer",
    # Analytics
    "AnalyticsEvent", "AnalyticsSession", "DailyMetric", "FeatureUsage",
    "CohortRetention", "AnalyticsAlert", "AnalyticsAccessLog",
    # Clustering
    "ClusteringModel", "ArchetypeDefinition", "ArchetypeAssignment",
    "ClusteringMonitoringLog",
    # Transfer
    "MarketValuation", "TransferHistory", "ContractStatus",
    # Org
    "Organization", "OrgMembership", "OrgSettings", "OrgInvite",
    "AuditLog", "Comment", "Mention",
    # Tactical
    "MatchPassingNetwork", "MatchSpatialAnalysis", "MatchFormation",
]
