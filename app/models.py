"""ORM models — the code-side mirror of `schema.sql`.

Every table, enum, and index here corresponds 1:1 to the canonical PostgreSQL
DDL in `schema.sql`. Enum columns are declared with native_enum=False so the
same models build a working SQLite database for tests; on PostgreSQL the
production DDL (with real CREATE TYPE enums) is applied via `schema.sql`.

Versioning/immutability design (Constitution §3, §6-11):
- stat_snapshots are append-only, versioned by (…, source, scrape_date).
- percentile_snapshots are written fresh on every computation run and never
  updated in place; is_published flips only once the anomaly gate passes.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Enums. native_enum=True (the SQLAlchemy default): PostgreSQL gets the real
# enum types that schema.sql's CREATE TYPE defines (same names), and SQLite —
# which has no native enums — automatically falls back to VARCHAR + CHECK, so
# the same models build a working SQLite test database. This is the C3 parity
# fix: with native_enum=False, SQLAlchemy 2.0's bulk inserts cast enum columns
# to VARCHAR, which PostgreSQL rejects ("column is of type X but expression is
# of type character varying").
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
    "transfermarkt",
    "understat_transfer",
    "instat",
    "manual",
    name="market_source",
)
TRANSFER_TYPE_ENUM = Enum(
    "permanent",
    "loan",
    "free_agent",
    name="transfer_type",
)
TRANSFER_STATUS_ENUM = Enum(
    "confirmed",
    "reported",
    name="transfer_status",
)
CONTRACT_STATUS_ENUM = Enum(
    "active",
    "expiring_next_season",
    "expired",
    "on_loan",
    name="contract_status",
)
VALUATION_CONFIDENCE_ENUM = Enum(
    "high",
    "medium",
    "low",
    name="valuation_confidence",
)
RISK_TIER_ENUM = Enum(
    "low",
    "medium",
    "high",
    name="risk_tier",
)
SUBSCRIPTION_STATUS_ENUM = Enum(
    "active",
    "trialing",
    "past_due",
    "canceled",
    "incomplete",
    name="subscription_status",
)
# Subscription plan (Constitution §1 business model: Free / Pro / API-Business).
PLAN_ENUM = Enum("free", "pro", "api_business", name="plan")
# Phase 7 — scouting workspace pipeline (docs/product/scouting-pipeline.md).
ENTRY_STATUS_ENUM = Enum(
    "discovered",
    "monitoring",
    "scouted",
    "shortlisted",
    "reviewed",
    "rejected",
    "signed",
    name="entry_status",
)
ENTRY_PRIORITY_ENUM = Enum("low", "medium", "high", name="entry_priority")
# Phase 10 — watchlist & alerts (docs/product/alert-trigger-definitions.md).
ENTITY_TYPE_ENUM = Enum("player", "team", name="entity_type")
ALERT_TYPE_ENUM = Enum(
    "percentile_movement",
    "club_change",
    "new_season_data",
    "data_coverage_change",
    name="alert_type",
)
DIGEST_FREQUENCY_ENUM = Enum(
    "immediate", "daily_digest", "weekly_digest", name="digest_frequency"
)


class Base(DeclarativeBase):
    pass


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str] = mapped_column(TIER_ENUM, nullable=False)
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # null until real assets exist

    __table_args__ = (
        UniqueConstraint("name", "league_id", name="uq_teams_name_league"),
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_position: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # natural-language label
    position_group: Mapped[str | None] = mapped_column(
        POSITION_GROUP_ENUM, nullable=True
    )
    external_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_players_canonical_name", "canonical_name"),
        Index("ix_players_position_group", "position_group"),
    )


class PlayerNameAlias(Base):
    __tablename__ = "player_name_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_name_string: Mapped[str] = mapped_column(String(128), nullable=False)
    player: Mapped[Player] = relationship()  # used by reconciliation._alias_lookup

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "source",
            "source_name_string",
            name="uq_alias_player_source_name",
        ),
        Index("ix_aliases_source_name", "source", "source_name_string"),
    )


class StatSnapshot(Base):
    __tablename__ = "stat_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    scrape_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # versioning key
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    raw_stats: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )  # metric id -> per-90 value
    minutes_played: Mapped[float] = mapped_column(Float, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        SNAPSHOT_STATUS_ENUM, nullable=False, default="ingested"
    )

    # Relationships (single-sided; the FK side owns the join). player/league are
    # used by the percentile and anomaly jobs (cohort grouping); team is not yet
    # consumed by pipeline code — kept for Phase 2 player-page queries.
    player: Mapped[Player] = relationship()
    team: Mapped[Team | None] = relationship()
    league: Mapped[League] = relationship()

    __table_args__ = (
        # Natural key -> idempotent re-runs (scrape_date + source + identity).
        UniqueConstraint(
            "player_id",
            "team_id",
            "league_id",
            "season",
            "source",
            "scrape_date",
            name="uq_stat_snapshot_natural_key",
        ),
        Index(
            "ix_stat_snapshot_league_season_scrape",
            "league_id",
            "season",
            "scrape_date",
        ),
        Index("ix_stat_snapshot_player", "player_id"),
        Index("ix_stat_snapshot_source", "source"),
    )


class PercentileSnapshot(Base):
    __tablename__ = "percentile_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("stat_snapshots.id"), nullable=False
    )
    computed_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    position_group: Mapped[str] = mapped_column(POSITION_GROUP_ENUM, nullable=False)
    league_tier: Mapped[str] = mapped_column(TIER_ENUM, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    percentile_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # denormalised per-row; see schema.sql comment
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        # Tier dimension in the unique key (C1 closeout): a same-season
        # cross-tier transfer must be able to carry percentile rows per tier
        # for the same metric without colliding. A stat_snapshot belongs to
        # one league/tier, so (snapshot, metric, tier) is the true identity.
        UniqueConstraint(
            "stat_snapshot_id",
            "metric_name",
            "league_tier",
            name="uq_percentile_snapshot_metric_tier",
        ),
        Index("ix_percentile_snapshot_published", "is_published"),
        Index("ix_percentile_snapshot_position_tier", "position_group", "league_tier"),
    )


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), nullable=True
    )  # null if unmatched
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    x_coordinate: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_coordinate: Mapped[float | None] = mapped_column(Float, nullable=True)
    minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_competition_id: Mapped[str] = mapped_column(String(64), nullable=False)
    season: Mapped[str | None] = mapped_column(String(16), nullable=True)
    extra: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # source-specific payload: shot xG, pass end coords, player name (Phase 3)

    __table_args__ = (
        UniqueConstraint("match_id", "event_id", name="uq_match_event"),
        Index("ix_match_events_competition", "source_competition_id"),
        Index("ix_match_events_player", "player_id"),
    )


class DataCoverage(Base):
    __tablename__ = "data_coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    seasons_available: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_successful_scrape: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        COVERAGE_STATUS_ENUM, nullable=False, default="active"
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "source_identifier", name="uq_coverage_source_identifier"
        ),
        CheckConstraint(
            "league_id IS NOT NULL OR source = 'statsbomb'",
            name="ck_coverage_league_optional",
        ),
    )


class IngestionAnomaly(Base):
    __tablename__ = "ingestion_anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("stat_snapshots.id"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_anomalies_unresolved", "resolved"),)


class ReconciliationQueue(Base):
    __tablename__ = "reconciliation_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(SOURCE_ENUM, nullable=False)
    source_record_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidate_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        QUEUE_STATUS_ENUM, nullable=False, default="pending"
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("source", "source_record_key", name="uq_queue_source_key"),
        Index("ix_queue_status", "status"),
    )


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(16), nullable=False)
    api_fixture_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    away_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    home_team_name: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team_name: Mapped[str] = mapped_column(String(128), nullable=False)
    kickoff_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("api_fixture_id", name="uq_fixture_api_id"),
        Index("ix_fixtures_league_season", "league_id", "season"),
    )


ACCOUNT_STATUS_ENUM = Enum(
    "active", "suspended", "pending_deletion", name="account_status"
)


class User(Base):
    """Statlas account (Phase 4 — Part A, extended Phase 12). Passwords are
    stored as PBKDF2-HMAC hashes (never plaintext — Constitution §4 security,
    D3); sessions are separate token rows. The `plan` column is a convenience
    mirror of the subscriptions table; access decisions always read
    `has_pro_access`."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(PLAN_ENUM, nullable=False, default="free")
    # Phase 12 — full identity fields
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    account_status: Mapped[str] = mapped_column(
        ACCOUNT_STATUS_ENUM, nullable=False, default="active"
    )
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    sessions: Mapped[list["SessionToken"]] = relationship(back_populates="user")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )


class SessionToken(Base):
    """Server-side session (Phase 4 — Part A auth). The token VALUE is never
    stored; only its SHA-256 hash, so a DB leak cannot be replayed as sessions.
    Expiry is enforced by `is_session_valid`."""

    __tablename__ = "session_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_session_token_hash"),
        Index("ix_session_user", "user_id"),
    )


class PasswordResetToken(Base):
    """Single-use, time-limited password-reset token (Phase 12 — Part B)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_password_reset_user", "user_id"),)


class EmailVerificationToken(Base):
    """Single-use, time-limited email-verification token (Phase 12 — Part B)."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_email_verification_user", "user_id"),)


class Subscription(Base):
    """The single source of truth for access decisions (Phase 4 — Part A4).
    `status` mirrors Stripe's subscription object; `grace_period_end` is set on
    payment failure so access persists through Stripe's dunning retries instead
    of an abrupt cutoff. Never infer access from scattered flags."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan: Mapped[str] = mapped_column(PLAN_ENUM, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    status: Mapped[str] = mapped_column(
        SUBSCRIPTION_STATUS_ENUM, nullable=False, default="incomplete"
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    grace_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscriptions_user", "user_id"),
        Index("ix_subscriptions_stripe_sub", "stripe_subscription_id"),
    )


class ApiKey(Base):
    """Public API key (Phase 4 — Part C). Only the SHA-256 hash of the key is
    stored; the plaintext is shown once at creation, then unrecoverable — the
    dashboard lists prefixes for identification. Revoked keys fail auth."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("key_hash", name="uq_api_key_hash"),
        Index("ix_api_keys_user", "user_id"),
    )


class WebhookEvent(Base):
    """Processed Stripe webhook log (Phase 4 — Part A3). The `event_id` unique
    constraint IS the idempotency mechanism: replaying an event hits the unique
    key and is recorded as a duplicate, never re-processed. Logs keep enough
    detail to reconstruct billing disputes."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_webhook_event_id"),
        Index("ix_webhook_events_type", "event_type"),
    )


# ---------------------------------------------------------------------------
# Phase 7 — Scouting workspace (shortlists, entries, notes, tags, history)
# ---------------------------------------------------------------------------
# Design notes (full rationale in docs/product/scouting-pipeline.md):
# * Ownership: every row is reachable only through shortlists.user_id — the
#   query layer verifies ownership on EVERY read/write and returns 404 for
#   foreign or missing ids (no existence leak).
# * Soft delete: remove_entry/delete_shortlist set removed_at/deleted_at —
#   scouting history is never silently destroyed (Constitution bias). Notes,
#   tags and status_history are retained for audit.
# * (shortlist_id, player_id) UNIQUE: a player can appear in many shortlists
#   but never twice in one. On a player merge/reconciliation the canonical
#   player_id must be reassigned on shortlist_entries (documented in the
#   pipeline doc) — the FK is RESTRICT so a merge cannot orphan rows silently.

# Phase 16 enums (used by Shortlist, SavedSearch, Report, Watch org columns)
ORG_ROLE_ENUM = Enum("owner", "manager", "scout", "viewer", name="org_role")
VISIBILITY_ENUM = Enum(
    "personal", "org_members", "restricted", name="resource_visibility"
)
ORG_TIER_ENUM = Enum("free", "pro", "enterprise", name="org_tier")


class Shortlist(Base):
    __tablename__ = "shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # soft delete — history preserved
    # Phase 16 — org ownership (null = personal, existing behavior)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    restricted_access: Mapped[list | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (Index("ix_shortlists_user", "user_id"),)


class ShortlistEntry(Base):
    __tablename__ = "shortlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_id: Mapped[int] = mapped_column(
        ForeignKey("shortlists.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        ENTRY_STATUS_ENUM, nullable=False, default="discovered"
    )
    priority: Mapped[str | None] = mapped_column(
        ENTRY_PRIORITY_ENUM, nullable=True
    )  # None = unset
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    added_by_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # why the player was added — captured at add time
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # soft delete — audit trail intact

    __table_args__ = (
        UniqueConstraint("shortlist_id", "player_id", name="uq_shortlist_entry_player"),
        Index("ix_entries_shortlist", "shortlist_id"),
        Index("ix_entries_player", "player_id"),
        Index("ix_entries_status", "status"),
    )


class EntryNote(Base):
    """Timestamped notes appended to an entry over time (a scouting
    relationship spans months — never a single overwritable text field)."""

    __tablename__ = "entry_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_notes_entry", "shortlist_entry_id"),)


class EntryTag(Base):
    """Free-form tags ("left-footed", "contract expiring") — normalized to
    lowercase so the same vocabulary never duplicates. Not a rigid taxonomy:
    suggestions come from the user's OWN tags (get_user_tag_suggestions)."""

    __tablename__ = "entry_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    tag_text: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("shortlist_entry_id", "tag_text", name="uq_entry_tag"),
        Index("ix_tags_entry", "shortlist_entry_id"),
    )


class StatusHistory(Base):
    """Auditable status changes: who moved the entry, from where, to where,
    when, and why. from_status is NULL for the initial creation row. This is
    what answers "how long in Monitoring?" / "who rejected this and why?"""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shortlist_entry_id: Mapped[int] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(ENTRY_STATUS_ENUM, nullable=True)
    to_status: Mapped[str] = mapped_column(ENTRY_STATUS_ENUM, nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_status_history_entry", "shortlist_entry_id"),)


# ---------------------------------------------------------------------------
# Phase 8 — structured search (saved searches + history)
# ---------------------------------------------------------------------------
# Grammar and rules: docs/product/query-builder-scope.md. Same ownership
# model as Phase 7: every read/write verifies user_id; foreign/missing ids
# return 404, never an existence-leaking 403. Presets are NOT tables — they
# live in app/config/search_presets.json (methodology-as-code precedent) and
# are public.


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Phase 16 — org ownership (null = personal, existing behavior)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (Index("ix_saved_searches_user", "user_id"),)


class SearchHistory(Base):
    """Automatic log of executed queries (never the debounced builder preview).
    Retention: newest 50 per user, enforced on insert (query-builder-scope.md §4)."""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_search_history_user", "user_id"),)


# ---------------------------------------------------------------------------
# Phase 9 — AI scouting reports (persisted, verified artifacts)
# ---------------------------------------------------------------------------
# Design (docs/product/scouting-reports.md): reports are per-user data with
# the Phase 7/8 ownership pattern (404 on foreign/missing ids, never a 403).
# `report_json` stores the FULL structured report (sections + evidence
# appendix + verification log) verbatim — exports derive from this one object.
# `verification.status` is "passed" or "needs_review" (a generated report whose
# claims failed the hard grounding gate is never silently shipped).


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    shortlist_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("shortlist_entries.id"), nullable=True
    )  # set only when generated from a Phase 7 shortlist entry
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="generated"
    )  # generated | needs_review
    data_snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # which stat_snapshot this report is based on (reproducibility)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    verification_log: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Phase 16 — org ownership (null = personal, existing behavior)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (Index("ix_reports_user", "user_id"),)


class ReportQuota(Base):
    """Per-user report-generation allowance (Phase 9 — D5). Deliberately
    SEPARATE from assistant_quotas: sharing one pool would cause confusing
    "why did my chat quota drop" experiences. Same hard-cap model and
    calendar-month reset as the assistant quota."""

    __tablename__ = "report_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reports_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reports_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_report_quota_period"),
    )


class Watch(Base):
    """A followed entity (Phase 10 — docs/product/alert-trigger-definitions.md
    §1/§4). One row per (user, entity_type, entity_id); followed_metrics is the
    optional per-metric refinement (null = broad "any significant movement")."""

    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(ENTITY_TYPE_ENUM, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    followed_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Phase 16 — org ownership (null = personal, existing behavior)
    owner_org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        VISIBILITY_ENUM, nullable=False, default="personal"
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_watch_entity"),
        Index("ix_watches_user", "user_id"),
        Index("ix_watches_entity", "entity_type", "entity_id"),
    )


class WatchAlert(Base):
    """One detected, trigger-worthy event (Phase 10). `detail` holds only real,
    traceable values from the snapshot/coverage/anomaly data that triggered it;
    `dedupe_key` makes detection idempotent (unique per watch+type+transition)."""

    __tablename__ = "watch_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int] = mapped_column(ForeignKey("watches.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(ALERT_TYPE_ENUM, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    watch: Mapped[Watch] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "watch_id", "alert_type", "dedupe_key", name="uq_watch_alert_dedupe"
        ),
        Index("ix_alerts_watch", "watch_id"),
        Index("ix_alerts_user_read", "dismissed", "read_at"),
    )


class NotificationPreferences(Base):
    """Per-user notification control (Phase 10 — §5). Opt-outs are absolute:
    delivery never sends an email for a disabled type or channel. The
    unsubscribe_token signs one-click email links (List-Unsubscribe)."""

    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_type_preferences: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    digest_frequency: Mapped[str] = mapped_column(
        DIGEST_FREQUENCY_ENUM, nullable=False, default="immediate"
    )
    unsubscribe_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()

    __table_args__ = (UniqueConstraint("user_id", name="uq_preferences_user"),)


class AssistantQuota(Base):
    """Per-user assistant query quota (Phase 4 — Part B3), tracked per billing
    period and reset on renewal. Hard cap (no silent overage) — the documented
    model per the Phase 4 prompt: users are blocked at the cap with the reset
    date stated, never billed past it."""

    __tablename__ = "assistant_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    queries_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queries_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped[User] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_assistant_quota_period"),
    )


# ---------------------------------------------------------------------------
# Phase 11 — Emerging player scores (computed during weekly refresh)
# ---------------------------------------------------------------------------
# One row per (player, league, computed_date). The score is a weighted
# composite of trend magnitude, consistency, age, and sample size — see
# docs/analytics/emerging-player-methodology.md for the full formula.
# Idempotency: re-running for the same computed_date replaces rows.


class EmergingPlayerScore(Base):
    __tablename__ = "emerging_player_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    computed_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    contributing_factors: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )  # {trend_magnitude, trend_consistency, age_weight, sample_weight, ...}

    player: Mapped[Player] = relationship()
    league: Mapped[League] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "league_id",
            "computed_date",
            name="uq_emerging_player_league_date",
        ),
        Index("ix_emerging_league_date", "league_id", "computed_date"),
        Index("ix_emerging_score", "league_id", "computed_date", "score"),
    )


# ---------------------------------------------------------------------------
# Phase 13 — Activity tracking, dashboard state, saved players
# ---------------------------------------------------------------------------


ENTITY_TYPE_ENUM_13 = Enum(
    "player",
    "team",
    "search",
    "shortlist",
    "report",
    "watch",
    name="entity_type_13",
)
ACTION_TYPE_ENUM = Enum(
    "viewed",
    "created",
    "edited",
    "deleted",
    "shared",
    "run",
    name="action_type",
)


class ActivityLog(Base):
    """Single source of truth for user activity (Phase 13 — Part A).
    Deduplication enforced at write time: same entity within 60s = skip.
    """

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(ENTITY_TYPE_ENUM_13, nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(ACTION_TYPE_ENUM, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_activity_user_time", "user_id", "performed_at"),
        Index(
            "ix_activity_entity",
            "user_id",
            "entity_type",
            "entity_id",
            "performed_at",
        ),
    )


class DashboardState(Base):
    """Per-user dashboard widget config + dismissed recommendations (Phase 13)."""

    __tablename__ = "dashboard_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    widget_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dismissed_recommendations: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", name="uq_dashboard_state_user"),)


class SavedPlayer(Base):
    """Lightweight bookmark — distinct from Phase 7 shortlists (Phase 13)."""

    __tablename__ = "saved_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "player_id", name="uq_saved_player_user_player"),
        Index("ix_saved_players_user", "user_id", "saved_at"),
    )


# ---------------------------------------------------------------------------
# Phase 14 — Player Clustering & Archetypes (ML platform)
# ---------------------------------------------------------------------------
# Design (ML Constitution Addendum §3):
# * Every model has a registry entry documenting provenance, metrics, and
#   governance status. Models are versioned — never silently overwritten.
# * Archetype assignments are deterministic per (player, model_version):
#   the same player with the same snapshot always gets the same archetype.
# * Archetype definitions are human-authored names + descriptions grounded
#   in cluster center statistics (Constitution §1.3 burden of explainability).
# * All training data is reproducible from a documented query/script.

CLUSTERING_STATUS_ENUM = Enum(
    "candidate", "in_production", "archived", name="clustering_status"
)


class ClusteringModel(Base):
    """Model registry entry (ML Constitution Addendum §3.1).
    Every production ML model has a unique versioned ID — never silently
    overwrite; every update is a new version number."""

    __tablename__ = "clustering_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. 'k-means'
    hyperparameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    n_clusters: Mapped[int] = mapped_column(Integer, nullable=False)
    training_data_source: Mapped[str] = mapped_column(String(256), nullable=False)
    training_data_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    training_data_features: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    silhouette_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    davies_bouldin_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    per_subgroup_scores: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    bias_audit_results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    training_code_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    training_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    staleness_months: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    status: Mapped[str] = mapped_column(
        CLUSTERING_STATUS_ENUM, nullable=False, default="candidate"
    )
    deployed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    known_limitations: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rollback_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "model_name", "version", name="uq_clustering_model_name_version"
        ),
        Index("ix_clustering_model_status", "status"),
    )


class ArchetypeDefinition(Base):
    """Human-authored archetype cluster definitions (Constitution §1.3).
    One row per (model_id, cluster_id). Names and descriptions are grounded
    in cluster center statistics — never arbitrary labels."""

    __tablename__ = "archetype_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("clustering_models.id"), nullable=False
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_center: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    distinguishing_features: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    example_players: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    model: Mapped["ClusteringModel"] = relationship()

    __table_args__ = (
        UniqueConstraint("model_id", "cluster_id", name="uq_archetype_model_cluster"),
        Index("ix_archetype_model", "model_id"),
    )


class ArchetypeAssignment(Base):
    """Per-player archetype assignment from a specific model version.
    Deterministic: same (player, model_version, snapshot_date) always yields
    the same archetype. distance_to_center is the confidence measure — lower
    means more typical of the archetype."""

    __tablename__ = "archetype_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("clustering_models.id"), nullable=False
    )
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_to_center: Mapped[float] = mapped_column(Float, nullable=False)
    top_distinguishing_features: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    computed_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    player: Mapped[Player] = relationship()
    model: Mapped["ClusteringModel"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "model_id",
            "snapshot_date",
            name="uq_archetype_assignment_player_model_date",
        ),
        Index("ix_archetype_assignment_player", "player_id"),
        Index("ix_archetype_assignment_model", "model_id", "cluster_id"),
    )


class ClusteringMonitoringLog(Base):
    """Weekly monitoring entries (ML Constitution Addendum §4).
    Tracks drift detection results, assignment churn, and retraining events."""

    __tablename__ = "clustering_monitoring_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("clustering_models.id"), nullable=False
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    log_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # drift, churn, retrain, alert
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metric_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_triggered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    model: Mapped["ClusteringModel"] = relationship()

    __table_args__ = (
        Index("ix_monitoring_model_time", "model_id", "logged_at"),
        Index("ix_monitoring_alerts", "alert_triggered"),
    )


# ---------------------------------------------------------------------------
# Phase 15 — Transfer Intelligence & Market Data
# ---------------------------------------------------------------------------
# Design (docs/product/transfer-intelligence.md):
# * All market data is versioned and append-only (Constitution §3).
# * Valuations carry a confidence level and source attribution.
# * Transfer history is real, confirmed data — never fabricated.
# * Contract status is a snapshot, not live data.


class MarketValuation(Base):
    """Market valuation for a player from a specific source.
    Idempotent per (player, source, valuation_date). Historical valuations
    are preserved — never overwritten. Every valuation carries source
    attribution and a confidence level."""

    __tablename__ = "market_valuations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    valuation_amount_eur: Mapped[float] = mapped_column(Float, nullable=False)
    valuation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    low_range: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_range: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[str] = mapped_column(
        VALUATION_CONFIDENCE_ENUM, nullable=False, default="medium"
    )
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player: Mapped[Player] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "source",
            "valuation_date",
            name="uq_market_valuation_player_source_date",
        ),
        Index("ix_market_valuation_player", "player_id", "valuation_date"),
        Index("ix_market_valuation_date", "valuation_date"),
    )


class TransferHistory(Base):
    """Confirmed or reported transfer record. Status distinguishes confirmed
    deals from reported/approximate information."""

    __tablename__ = "transfer_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    from_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    to_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    transfer_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reported_fee_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    transfer_type: Mapped[str] = mapped_column(TRANSFER_TYPE_ENUM, nullable=False)
    status: Mapped[str] = mapped_column(
        TRANSFER_STATUS_ENUM, nullable=False, default="reported"
    )
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player: Mapped[Player] = relationship()
    from_team: Mapped[Team | None] = relationship(foreign_keys=[from_team_id])
    to_team: Mapped[Team] = relationship(foreign_keys=[to_team_id])

    __table_args__ = (
        Index("ix_transfer_player", "player_id"),
        Index("ix_transfer_date", "transfer_date"),
        Index("ix_transfer_to_team", "to_team_id"),
    )


class ContractStatus(Base):
    """Contract status snapshot for a player. Updated periodically, not live."""

    __tablename__ = "contract_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    current_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    contract_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    contract_value_per_year_eur: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    contract_status: Mapped[str] = mapped_column(
        CONTRACT_STATUS_ENUM, nullable=False, default="active"
    )
    source: Mapped[str] = mapped_column(MARKET_SOURCE_ENUM, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    player: Mapped[Player] = relationship()
    current_team: Mapped[Team | None] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "source",
            "snapshot_date",
            name="uq_contract_status_player_source_date",
        ),
        Index("ix_contract_player", "player_id"),
    )


# ---------------------------------------------------------------------------
# Phase 16 — Organization / Multi-Tenant Architecture
# ---------------------------------------------------------------------------
# Design (Multi-Tenant Architecture Addendum):
# * Every existing user-owned resource (shortlists, searches, reports, watches)
#   gains an optional owner_org_id column. null = personal (existing behavior).
# * RBAC is enforced at the query layer via user_has_permission() — every
#   read/write checks membership + role before returning data.
# * Org membership is opt-in: solo users continue working unchanged.
# * Audit logging captures all team-structure changes.

ORG_ROLE_ENUM = Enum("owner", "manager", "scout", "viewer", name="org_role")
VISIBILITY_ENUM = Enum(
    "personal", "org_members", "restricted", name="resource_visibility"
)
ORG_TIER_ENUM = Enum("free", "pro", "enterprise", name="org_tier")


class Organization(Base):
    """Top-level organization entity. Owners are users who created the org.
    Slug is for org branding/public URLs. Tier governs seat limits and features."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tier: Mapped[str] = mapped_column(ORG_TIER_ENUM, nullable=False, default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    primary_contact_email: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    billing_contact_email: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_organizations_slug", "slug"),
        Index("ix_organizations_owner", "owner_user_id"),
    )


class OrgMembership(Base):
    """Org membership with role. One row per (org, user). The role governs
    what the user can do within the org (RBAC permission matrix)."""

    __tablename__ = "org_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(ORG_ROLE_ENUM, nullable=False, default="scout")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    invited_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    permissions_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_membership"),
        Index("ix_org_memberships_org", "org_id"),
        Index("ix_org_memberships_user", "user_id"),
    )


class OrgSettings(Base):
    """Per-org configuration. One row per org (created on org creation)."""

    __tablename__ = "org_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), unique=True, nullable=False
    )
    data_retention_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    workspace_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enable_audit_logging: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    allow_public_reporting: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    require_2fa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (Index("ix_org_settings_org", "org_id"),)


ORG_INVITE_STATUS_ENUM = Enum(
    "pending", "accepted", "expired", name="org_invite_status"
)


class OrgInvite(Base):
    """Pending org invitation. Time-limited token, single-use."""

    __tablename__ = "org_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(ORG_ROLE_ENUM, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        ORG_INVITE_STATUS_ENUM, nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_org_invites_org", "org_id"),
        Index("ix_org_invites_token", "token_hash"),
    )


AUDIT_ACTION_ENUM = Enum(
    "user_added",
    "user_removed",
    "role_changed",
    "resource_created",
    "resource_shared",
    "resource_deleted",
    "comment_added",
    name="audit_action",
)


class AuditLog(Base):
    """Append-only audit trail for org events. Only readable by owner/manager."""

    __tablename__ = "org_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    action: Mapped[str] = mapped_column(AUDIT_ACTION_ENUM, nullable=False)
    performed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    resource_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_org", "org_id", "created_at"),
        Index("ix_audit_log_performed_by", "performed_by_user_id"),
    )


# ---------------------------------------------------------------------------
# Phase 16 — Comments & Collaboration
# ---------------------------------------------------------------------------


class Comment(Base):
    """Comment on a shared resource (shortlist, report, search). Supports
    threading (parent_id = null for top-level, parent_id = comment.id for reply).
    Soft-deleted via deleted_at."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_comments_resource", "resource_type", "resource_id"),
        Index("ix_comments_org", "org_id", "created_at"),
        Index("ix_comments_author", "author_user_id"),
    )


MENTION_STATUS_ENUM = Enum("pending", "read", name="mention_status")


class Mention(Base):
    """A @username mention in a comment. Triggers a notification."""

    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id"), nullable=False)
    mentioned_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        MENTION_STATUS_ENUM, nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_mentions_user", "mentioned_user_id", "status"),
        Index("ix_mentions_comment", "comment_id"),
    )


# ---------------------------------------------------------------------------
# Phase 17 — Tactical Intelligence (passing networks, heatmaps, formations)
# ---------------------------------------------------------------------------
# Design (docs/analytics/phase17-data-coverage.md):
# * All tactical data is derived from StatsBomb event data.
# * Coverage-gating: only matches with sufficient event data are analyzed.
# * Cached per match to avoid recomputation.


class MatchPassingNetwork(Base):
    """Cached passing network graph for a match/team.

    Stores the precomputed directed graph (nodes + edges) with network
    metrics. Built on first request, cached for subsequent queries.
    """

    __tablename__ = "match_passing_networks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="full_match")
    network_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    style_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    anomalies_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "team_id",
            "phase",
            name="uq_passing_network_match_team_phase",
        ),
        Index("ix_passing_network_match", "match_id"),
    )


class MatchSpatialAnalysis(Base):
    """Cached spatial analysis (pressure/possession heatmaps) for a match/team."""

    __tablename__ = "match_spatial_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    analysis_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pressure, possession, pressure_success
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "team_id",
            "analysis_type",
            name="uq_spatial_analysis_match_team_type",
        ),
        Index("ix_spatial_analysis_match", "match_id"),
    )


class MatchFormation(Base):
    """Cached formation detection and stability analysis for a match/team."""

    __tablename__ = "match_formations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    detected_formation: Mapped[str] = mapped_column(String(16), nullable=False)
    stability_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    conformity_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "team_id",
            name="uq_formation_match_team",
        ),
        Index("ix_formation_match", "match_id"),
    )


# ---------------------------------------------------------------------------
# Phase 18 — Internal Usage Analytics
# ---------------------------------------------------------------------------
# Constitution §3: all data is append-only, versioned by timestamp.
# Constitution §6: no fabricated numbers — events are real, metrics derived.

class AnalyticsEvent(Base):
    """Raw analytics event — the atomic unit of user behavior tracking.

    Events are append-only.  Aggregation into DAU/MAU/retention happens in
    compute functions, never by mutating these rows.
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_analytics_event_name_time", "event_name", "created_at"),
        Index("ix_analytics_event_user", "user_id", "created_at"),
        Index("ix_analytics_event_session", "session_id", "created_at"),
    )


class AnalyticsSession(Base):
    """Aggregated session record — built from raw events.

    A session = continuous period of user activity.  Ends after 30 minutes
    of inactivity (Phase 18 Part A3).
    """

    __tablename__ = "analytics_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    events_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    device_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(32), nullable=True)
    os: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index("ix_session_user_time", "user_id", "started_at"),
    )


class DailyMetric(Base):
    """Pre-computed daily metrics — one row per metric per day per tier.

    Allows fast dashboard queries without scanning raw events every time.
    """

    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "metric_date", "metric_name", "tier",
            name="uq_daily_metric",
        ),
        Index("ix_daily_metric_name_date", "metric_name", "metric_date"),
    )


class FeatureUsage(Base):
    """Pre-computed feature adoption/engagement — one row per feature per day."""

    __tablename__ = "feature_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usage_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    feature_name: Mapped[str] = mapped_column(String(64), nullable=False)
    adoption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_engagement_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "usage_date", "feature_name",
            name="uq_feature_usage",
        ),
        Index("ix_feature_usage_date", "usage_date"),
    )


class CohortRetention(Base):
    """Cohort retention — one row per cohort month per months-since-signup."""

    __tablename__ = "cohort_retention"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_month: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    months_since_signup: Mapped[int] = mapped_column(Integer, nullable=False)
    cohort_size: Mapped[int] = mapped_column(Integer, nullable=False)
    retained_count: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_pct: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "cohort_month", "months_since_signup",
            name="uq_cohort_retention",
        ),
        Index("ix_cohort_retention_month", "cohort_month"),
    )


class AnalyticsAlert(Base):
    """Threshold/anomaly alerts — one row per alert fired."""

    __tablename__ = "analytics_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_alert_fired", "fired_at"),
        Index("ix_alert_name", "alert_name"),
    )


class AnalyticsAccessLog(Base):
    """Audit log for analytics dashboard access — who queried what, when."""

    __tablename__ = "analytics_access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    dashboard_name: Mapped[str] = mapped_column(String(64), nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_access_log_user", "user_id", "accessed_at"),
    )
