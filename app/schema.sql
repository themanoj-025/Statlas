-- ============================================================================
-- STATLAS — PHASE 1 DATABASE SCHEMA (PostgreSQL, canonical DDL)
-- Mirror of models.py. Apply with:  psql $DATABASE_URL -f schema.sql
--
-- DESIGN PRINCIPLES (Constitution §3, §6):
--   1. Time-series data is append-only and versioned by scrape date. Nothing
--      is mutated in place; a "correction" is a new snapshot row.
--   2. stat_snapshots carry the natural key (player, team, league, season,
--      source, scrape_date) so re-running a weekly job is idempotent: the
--      upsert skips existing rows instead of duplicating them.
--   3. percentile_snapshots are written fresh on every computation run and
--      keyed by (stat_snapshot_id, metric_name). index_score is denormalised
--      onto the "si_index" metric row (percentile_value IS NULL there); a
--      snapshot's percentile rows are only queryable once is_published=true,
--      which is set only after anomaly checks pass.
--   4. The anomaly gate (ingestion_anomalies) blocks publication: a player
--      with an unresolved anomaly is excluded from percentile pools.
--   5. data_coverage is the single source of truth for what data exists —
--      the UI may only claim what this table contains.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE source AS ENUM ('fbref', 'understat', 'statsbomb', 'api_football');
CREATE TYPE position_group AS ENUM ('GK', 'CB', 'FB', 'DM', 'CM', 'AM', 'W', 'ST');
CREATE TYPE snapshot_status AS ENUM ('ingested', 'flagged', 'published', 'failed');
CREATE TYPE coverage_status AS ENUM ('active', 'stale', 'failed');
CREATE TYPE league_tier AS ENUM ('tier_1', 'tier_2', 'tier_3');
CREATE TYPE queue_status AS ENUM ('pending', 'resolved', 'ignored');
CREATE TYPE plan AS ENUM ('free', 'pro', 'api_business');
CREATE TYPE subscription_status AS ENUM ('active', 'trialing', 'past_due', 'canceled', 'incomplete');
CREATE TYPE entry_status AS ENUM ('discovered', 'monitoring', 'scouted', 'shortlisted', 'reviewed', 'rejected', 'signed');
CREATE TYPE entry_priority AS ENUM ('low', 'medium', 'high');

-- ---------------------------------------------------------------------------
-- Core entities
-- ---------------------------------------------------------------------------

CREATE TABLE leagues (
    id            SERIAL PRIMARY KEY,
    slug          VARCHAR(64)  NOT NULL UNIQUE,          -- canonical slug (config/tiers.json)
    name          VARCHAR(128) NOT NULL,
    country       VARCHAR(64)  NOT NULL,
    tier          league_tier  NOT NULL,                 -- percentile grouping dimension
    external_ids  JSONB        NOT NULL DEFAULT '{}',    -- {fbref_comp, understat, api_football}
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE teams (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(128) NOT NULL,
    league_id     INTEGER      NOT NULL REFERENCES leagues(id),
    external_ids  JSONB        NOT NULL DEFAULT '{}',
    founded_year  INTEGER,                               -- null until sourced
    logo_url      TEXT,                                  -- NULL until real assets exist; never fabricated
    UNIQUE (name, league_id)
);

CREATE TABLE players (
    id              SERIAL PRIMARY KEY,
    canonical_name  VARCHAR(128) NOT NULL,
    date_of_birth   DATE,
    nationality     VARCHAR(64),
    primary_position VARCHAR(64),                        -- natural-language position label
    position_group  position_group,                      -- index grouping (methodology.md §3)
    external_ids    JSONB        NOT NULL DEFAULT '{}',  -- {fbref: id8, understat: id}
    current_team_id INTEGER      REFERENCES teams(id),   -- nullable for free agents
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_players_canonical_name ON players (canonical_name);
CREATE INDEX ix_players_position_group ON players (position_group);
CREATE INDEX ix_players_external_ids   ON players USING GIN (external_ids);

-- Name-reconciliation store: a permanent, auditable mapping between a source's
-- spelling of a player and the canonical player. Separate from players so a
-- corrected alias is a row edit, never a destructive rename, and lookups stay
-- index hits instead of fuzzy scans (see reconciliation.py rationale).
CREATE TABLE player_name_aliases (
    id                 SERIAL PRIMARY KEY,
    player_id          INTEGER      NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    source             source       NOT NULL,
    source_name_string VARCHAR(128) NOT NULL,
    UNIQUE (player_id, source, source_name_string)
);
CREATE INDEX ix_aliases_source_name ON player_name_aliases (source, source_name_string);

-- ---------------------------------------------------------------------------
-- Time-series / snapshot tables (append-only — the Constitution's versioning)
-- ---------------------------------------------------------------------------

-- One row per (player, team, league, season, source, scrape_date): the raw
-- per-metric payload for that scrape. raw_stats is keyed by registry metric id
-- and holds per-90 values / rates as the index consumes them, plus '_'-prefixed
-- sample-floor counters (_cmp_attempts, _sota_faced, _crosses_faced).
CREATE TABLE stat_snapshots (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER      NOT NULL REFERENCES players(id),
    team_id         INTEGER      REFERENCES teams(id),
    league_id       INTEGER      NOT NULL REFERENCES leagues(id),
    season          VARCHAR(16)  NOT NULL,               -- canonical '2025-26'
    scrape_date     TIMESTAMPTZ  NOT NULL,               -- VERSIONING KEY
    source          source       NOT NULL,
    raw_stats       JSONB        NOT NULL DEFAULT '{}',
    minutes_played  DOUBLE PRECISION NOT NULL,
    matches_played  INTEGER      NOT NULL DEFAULT 0,
    status          snapshot_status NOT NULL DEFAULT 'ingested',
    -- Idempotency natural key: re-scraping the same date+source is a no-op.
    UNIQUE (player_id, team_id, league_id, season, source, scrape_date)
);
CREATE INDEX ix_stat_snapshot_league_season_scrape ON stat_snapshots (league_id, season, scrape_date);
CREATE INDEX ix_stat_snapshot_player            ON stat_snapshots (player_id);
CREATE INDEX ix_stat_snapshot_source            ON stat_snapshots (source);

-- Percentiles + index scores per computation run. NEVER updated in place:
-- a recomputation after a data correction writes rows for a NEW scrape_date.
-- index_score is carried on the metric row metric_name='si_index'
-- (percentile_value IS NULL there) — the query layer reads it directly.
CREATE TABLE percentile_snapshots (
    id                SERIAL PRIMARY KEY,
    stat_snapshot_id  INTEGER      NOT NULL REFERENCES stat_snapshots(id),
    computed_date     TIMESTAMPTZ  NOT NULL,             -- the run that produced these rows
    position_group    position_group NOT NULL,
    league_tier       league_tier  NOT NULL,
    metric_name       VARCHAR(64)  NOT NULL,             -- registry metric id or 'si_index'
    percentile_value  DOUBLE PRECISION,                  -- NULL for the index row
    index_score       DOUBLE PRECISION,                  -- denormalised index value per run
    is_published      BOOLEAN      NOT NULL DEFAULT FALSE, -- the anomaly gate; queries read only TRUE
    -- C1 closeout: tier dimension added to the unique key. A stat_snapshot
    -- belongs to one league/tier, so (snapshot, metric, tier) is the true
    -- identity — a same-season cross-tier transfer keeps rows per tier.
    UNIQUE (stat_snapshot_id, metric_name, league_tier)
);
CREATE INDEX ix_percentile_published         ON percentile_snapshots (is_published);
CREATE INDEX ix_percentile_position_tier     ON percentile_snapshots (position_group, league_tier);
CREATE INDEX ix_percentile_snapshot_id       ON percentile_snapshots (stat_snapshot_id);

-- StatsBomb Open Data event-level data (shot/pass maps). Coverage is NOT
-- comprehensive across leagues — match_events is only populated for the
-- competitions that data_coverage says were actually synced.
CREATE TABLE match_events (
    id                      SERIAL PRIMARY KEY,
    match_id                VARCHAR(64) NOT NULL,
    event_id                VARCHAR(64) NOT NULL,
    player_id               INTEGER     REFERENCES players(id),  -- NULL until reconciled
    event_type              VARCHAR(64) NOT NULL,
    x_coordinate            DOUBLE PRECISION,
    y_coordinate            DOUBLE PRECISION,
    minute                  DOUBLE PRECISION,
    outcome                 VARCHAR(32),
    source_competition_id   VARCHAR(64) NOT NULL,
    season                  VARCHAR(16),
    extra                   JSONB,                                -- source-specific payload (shot xG, pass end coords, player name)
    UNIQUE (match_id, event_id)
);
CREATE INDEX ix_match_events_competition ON match_events (source_competition_id);
CREATE INDEX ix_match_events_player      ON match_events (player_id);

-- ---------------------------------------------------------------------------
-- Coverage & data-quality tables
-- ---------------------------------------------------------------------------

-- The single source of truth for "what data exists" (Constitution §3). The
-- /data-coverage page renders from this; UI features are gated on it.
CREATE TABLE data_coverage (
    id                     SERIAL PRIMARY KEY,
    league_id              INTEGER REFERENCES leagues(id),
    source                 source       NOT NULL,
    source_identifier      VARCHAR(128) NOT NULL,        -- league slug, or 'statsbomb:<comp>:<season>'
    seasons_available      JSONB        NOT NULL DEFAULT '[]',
    last_successful_scrape TIMESTAMPTZ,
    status                 coverage_status NOT NULL DEFAULT 'active',
    UNIQUE (source, source_identifier),
    CHECK (league_id IS NOT NULL OR source = 'statsbomb')
);

-- Concrete implementation of the anomaly-detection pass: a flagged value is
-- never published; it must be resolved (or explicitly overridden with a note)
-- before the owning player enters a percentile pool.
CREATE TABLE ingestion_anomalies (
    id               SERIAL PRIMARY KEY,
    stat_snapshot_id INTEGER REFERENCES stat_snapshots(id),  -- NULL for cross-source flags
    field_name       VARCHAR(64)  NOT NULL,                  -- metric id or 'cross_source:<id>'
    raw_value        TEXT,
    expected_range   TEXT,
    flagged_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    resolved         BOOLEAN      NOT NULL DEFAULT FALSE,
    resolution_note  TEXT
);
CREATE INDEX ix_anomalies_unresolved ON ingestion_anomalies (resolved);

-- Manual name-reconciliation queue: unmatched source records await a human
-- decision; resolving writes a permanent player_name_aliases row.
CREATE TABLE reconciliation_queue (
    id                  SERIAL PRIMARY KEY,
    source              source       NOT NULL,
    source_record_key   VARCHAR(128) NOT NULL,           -- external id or name
    source_name         VARCHAR(128) NOT NULL,
    source_team         VARCHAR(128),
    candidate_player_id INTEGER      REFERENCES players(id),
    status              queue_status NOT NULL DEFAULT 'pending',
    confidence          DOUBLE PRECISION,
    notes               TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ,
    UNIQUE (source, source_record_key)
);
CREATE INDEX ix_queue_status ON reconciliation_queue (status);

-- API-Football fixtures / live-scores layer (the only "live" data in the
-- product; never republished raw — renders as schedule/live UI only).
CREATE TABLE fixtures (
    id             SERIAL PRIMARY KEY,
    league_id      INTEGER      NOT NULL REFERENCES leagues(id),
    season         VARCHAR(16)  NOT NULL,
    api_fixture_id INTEGER      NOT NULL,
    home_team_id   INTEGER      REFERENCES teams(id),
    away_team_id   INTEGER      REFERENCES teams(id),
    home_team_name VARCHAR(128) NOT NULL,
    away_team_name VARCHAR(128) NOT NULL,
    kickoff_utc    TIMESTAMPTZ,
    status         VARCHAR(32),
    raw            JSONB        NOT NULL DEFAULT '{}',
    UNIQUE (api_fixture_id)
);
CREATE INDEX ix_fixtures_league_season ON fixtures (league_id, season);

-- ===========================================================================
-- Phase 4 — Monetization & accounts (Stripe subscriptions, auth, public API)
-- ===========================================================================
-- Design notes:
-- * users.plan is a convenience mirror; access decisions ALWAYS read the
--   subscriptions table via has_pro_access() — never scattered flags.
-- * Password hashes are PBKDF2-HMAC-SHA256 (auth.py) — never plaintext.
-- * Session/API key VALUES are never stored; only SHA-256 hashes, so a DB
--   leak cannot be replayed. API keys show once at creation (prefix only after).
-- * webhook_events.event_id UNIQUE is the idempotency mechanism: replays are
--   recorded as duplicates, never re-processed.
-- * Grace periods (grace_period_end) preserve access through Stripe's dunning
--   retries instead of an abrupt cutoff on first payment failure.

CREATE TYPE account_status AS ENUM ('active', 'suspended', 'pending_deletion');

CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    email            VARCHAR(320)  NOT NULL UNIQUE,
    password_hash    VARCHAR(255)  NOT NULL,
    plan             plan          NOT NULL DEFAULT 'free',
    display_name     VARCHAR(128),
    email_verified_at TIMESTAMPTZ,
    account_status   account_status NOT NULL DEFAULT 'active',
    timezone         VARCHAR(64),
    locale           VARCHAR(10),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_email ON users (email);

CREATE TABLE session_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX ix_session_user ON session_tokens (user_id);

CREATE TABLE password_reset_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ
);
CREATE INDEX ix_password_reset_user ON password_reset_tokens (user_id);

CREATE TABLE email_verification_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ
);
CREATE INDEX ix_email_verification_user ON email_verification_tokens (user_id);

CREATE TABLE subscriptions (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER      NOT NULL REFERENCES users(id),
    plan                    plan         NOT NULL,
    stripe_customer_id      VARCHAR(128),
    stripe_subscription_id  VARCHAR(128),
    status                  subscription_status NOT NULL DEFAULT 'incomplete',
    current_period_end      TIMESTAMPTZ,
    grace_period_end        TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_subscriptions_user ON subscriptions (user_id);
CREATE INDEX ix_subscriptions_stripe_sub ON subscriptions (stripe_subscription_id);

CREATE TABLE api_keys (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER      NOT NULL REFERENCES users(id),
    name         VARCHAR(128) NOT NULL,
    key_hash     VARCHAR(64)  NOT NULL UNIQUE,
    prefix       VARCHAR(12)  NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at   TIMESTAMPTZ
);
CREATE INDEX ix_api_keys_user ON api_keys (user_id);

CREATE TABLE webhook_events (
    id                      SERIAL PRIMARY KEY,
    event_id                VARCHAR(128) NOT NULL UNIQUE,
    event_type              VARCHAR(128) NOT NULL,
    stripe_subscription_id  VARCHAR(128),
    user_id                 INTEGER REFERENCES users(id),
    payload                 JSONB NOT NULL DEFAULT '{}',
    processed_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    duplicate               BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_webhook_events_type ON webhook_events (event_type);

CREATE TABLE assistant_quotas (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER     NOT NULL REFERENCES users(id),
    period_start  TIMESTAMPTZ NOT NULL,
    period_end    TIMESTAMPTZ NOT NULL,
    queries_used  INTEGER     NOT NULL DEFAULT 0,
    queries_limit INTEGER     NOT NULL,
    UNIQUE (user_id, period_start)
);

-- ===========================================================================
-- Phase 7 — Scouting workspace (shortlists, tags, notes, status pipeline)
-- ===========================================================================
-- Design notes (full rationale in docs/product/scouting-pipeline.md):
-- * Ownership: every row is reachable only through shortlists.user_id. The
--   query layer verifies ownership on EVERY read/write and returns 404 for
--   foreign or missing ids — never a 403 that would leak a shortlist's
--   existence to another user.
-- * Soft delete: shortlist_entries.removed_at and shortlists.deleted_at keep
--   scouting history auditable; notes/tags/status_history are never deleted.
-- * UNIQUE (shortlist_id, player_id): a player can sit in many shortlists
--   but never twice in one.
-- * Player merges (name reconciliation): shortlist_entries.player_id follows
--   the canonical player — a merge must reassign these rows (FK is RESTRICT,
--   so a merge can never silently orphan scouting data).

CREATE TABLE shortlists (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES users(id),
    name        VARCHAR(128) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ,                -- soft delete — history preserved
    -- Phase 16 — org ownership (null = personal, existing behavior)
    owner_org_id     INTEGER REFERENCES organizations(id),
    visibility       resource_visibility NOT NULL DEFAULT 'personal',
    created_by_user_id INTEGER REFERENCES users(id),
    restricted_access JSONB                  -- array of user_ids if visibility='restricted'
);
CREATE INDEX ix_shortlists_user ON shortlists (user_id);

CREATE TABLE shortlist_entries (
    id             SERIAL PRIMARY KEY,
    shortlist_id   INTEGER      NOT NULL REFERENCES shortlists(id),
    player_id      INTEGER      NOT NULL REFERENCES players(id),
    status         entry_status NOT NULL DEFAULT 'discovered',
    priority       entry_priority,                     -- NULL = unset
    added_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    added_by_note  TEXT,                                -- captured at add time
    removed_at     TIMESTAMPTZ,                         -- soft delete — audit intact
    UNIQUE (shortlist_id, player_id)
);
CREATE INDEX ix_entries_shortlist ON shortlist_entries (shortlist_id);
CREATE INDEX ix_entries_player    ON shortlist_entries (player_id);
CREATE INDEX ix_entries_status    ON shortlist_entries (status);

CREATE TABLE entry_notes (
    id                 SERIAL PRIMARY KEY,
    shortlist_entry_id INTEGER     NOT NULL REFERENCES shortlist_entries(id),
    author_user_id     INTEGER     NOT NULL REFERENCES users(id),
    note_text          TEXT        NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_notes_entry ON entry_notes (shortlist_entry_id);

CREATE TABLE entry_tags (
    id                 SERIAL PRIMARY KEY,
    shortlist_entry_id INTEGER     NOT NULL REFERENCES shortlist_entries(id),
    tag_text           VARCHAR(64) NOT NULL,             -- normalized lowercase
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (shortlist_entry_id, tag_text)
);
CREATE INDEX ix_tags_entry ON entry_tags (shortlist_entry_id);

CREATE TABLE status_history (
    id                  SERIAL PRIMARY KEY,
    shortlist_entry_id  INTEGER      NOT NULL REFERENCES shortlist_entries(id),
    from_status         entry_status,                    -- NULL on initial creation
    to_status           entry_status  NOT NULL,
    changed_by_user_id  INTEGER      NOT NULL REFERENCES users(id),
    changed_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    reason_note         TEXT
);
CREATE INDEX ix_status_history_entry ON status_history (shortlist_entry_id);

-- ===========================================================================
-- Phase 8 — Structured search (saved searches + history)
-- ===========================================================================
-- Grammar + rules in docs/product/query-builder-scope.md. Same ownership
-- model as Phase 7: every read/write verifies user_id; foreign/missing ids
-- return 404. search_presets is deliberately NOT a table — presets are
-- Statlas-authored config (app/config/search_presets.json), public by design.

CREATE TABLE saved_searches (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER     NOT NULL REFERENCES users(id),
    name             VARCHAR(128) NOT NULL,
    description      TEXT,
    query_definition JSONB       NOT NULL,               -- the structured condition model
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run_at      TIMESTAMPTZ,                        -- set on every re-run
    -- Phase 16 — org ownership
    owner_org_id     INTEGER REFERENCES organizations(id),
    visibility       resource_visibility NOT NULL DEFAULT 'personal',
    created_by_user_id INTEGER REFERENCES users(id)
);
CREATE INDEX ix_saved_searches_user ON saved_searches (user_id);

CREATE TABLE search_history (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER     NOT NULL REFERENCES users(id),
    query_definition JSONB       NOT NULL,
    executed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    result_count     INTEGER     NOT NULL DEFAULT 0
);
CREATE INDEX ix_search_history_user ON search_history (user_id);

-- ===========================================================================
-- Phase 9 — AI scouting reports (persisted, verified artifacts)
-- ===========================================================================
-- Design (docs/product/scouting-reports.md): reports are per-user data with
-- the Phase 7/8 ownership pattern (foreign/missing ids -> 404, never a 403
-- that leaks existence). report_json stores the FULL structured report
-- (sections + evidence appendix + verification log) verbatim — JSON/PDF/CSV
-- exports all derive from this one object. verification status is
-- 'passed' or 'needs_review' — a report whose claims failed the hard
-- grounding gate is never silently shipped as a normal report.
-- Phase 10 — watchlist & alerts (docs/product/alert-trigger-definitions.md).

CREATE TYPE entity_type AS ENUM ('player', 'team');
CREATE TYPE alert_type AS ENUM ('percentile_movement', 'club_change', 'new_season_data', 'data_coverage_change');
CREATE TYPE digest_frequency AS ENUM ('immediate', 'daily_digest', 'weekly_digest');

CREATE TABLE watches (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER      NOT NULL REFERENCES users(id),
    entity_type      entity_type  NOT NULL,
    entity_id        INTEGER      NOT NULL,
    followed_metrics JSONB,                    -- nullable; null = broad "any significant movement"
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    -- Phase 16 — org ownership
    owner_org_id     INTEGER REFERENCES organizations(id),
    visibility       resource_visibility NOT NULL DEFAULT 'personal',
    created_by_user_id INTEGER REFERENCES users(id),
    UNIQUE (user_id, entity_type, entity_id)   -- a user follows an entity once
);
CREATE INDEX ix_watches_user ON watches (user_id);
CREATE INDEX ix_watches_entity ON watches (entity_type, entity_id);

CREATE TABLE watch_alerts (
    id            SERIAL PRIMARY KEY,
    watch_id      INTEGER      NOT NULL REFERENCES watches(id),
    alert_type    alert_type   NOT NULL,
    dedupe_key    VARCHAR(160) NOT NULL,       -- idempotency: unique per watch+type+transition
    triggered_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    detail        JSONB        NOT NULL,       -- real, traceable values from the triggering data
    delivered_at  TIMESTAMPTZ,
    read_at       TIMESTAMPTZ,
    dismissed     BOOLEAN      NOT NULL DEFAULT FALSE,
    UNIQUE (watch_id, alert_type, dedupe_key)
);
CREATE INDEX ix_alerts_watch ON watch_alerts (watch_id);
CREATE INDEX ix_alerts_user_read ON watch_alerts (dismissed, read_at);

CREATE TABLE notification_preferences (
    id                     SERIAL PRIMARY KEY,
    user_id                INTEGER         NOT NULL REFERENCES users(id),
    email_enabled          BOOLEAN         NOT NULL DEFAULT TRUE,
    alert_type_preferences JSONB           NOT NULL DEFAULT '{}',   -- per-trigger-type opt-in/out
    digest_frequency       digest_frequency NOT NULL DEFAULT 'immediate',
    unsubscribe_token      VARCHAR(64),                              -- signs one-click email links
    updated_at             TIMESTAMPTZ     NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- report_quotas is deliberately SEPARATE from assistant_quotas so report
-- generation never silently drains the chat quota (D5 decision).

CREATE TABLE reports (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER     NOT NULL REFERENCES users(id),
    player_id             INTEGER     NOT NULL REFERENCES players(id),
    shortlist_entry_id    INTEGER     REFERENCES shortlist_entries(id),  -- set only when generated from a workspace entry
    status                VARCHAR(16) NOT NULL DEFAULT 'generated',      -- generated | needs_review
    data_snapshot_date    TIMESTAMPTZ NOT NULL,                          -- which snapshot this report is based on
    report_json           JSONB       NOT NULL,                          -- the full structured report (canonical export source)
    verification_log      JSONB       NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Phase 16 — org ownership
    owner_org_id          INTEGER REFERENCES organizations(id),
    visibility            resource_visibility NOT NULL DEFAULT 'personal',
    created_by_user_id    INTEGER REFERENCES users(id)
);
CREATE INDEX ix_reports_user ON reports (user_id);

CREATE TABLE report_quotas (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER     NOT NULL REFERENCES users(id),
    period_start  TIMESTAMPTZ NOT NULL,
    period_end    TIMESTAMPTZ NOT NULL,
    reports_used  INTEGER     NOT NULL DEFAULT 0,
    reports_limit INTEGER     NOT NULL,
    UNIQUE (user_id, period_start)
);

-- ===========================================================================
-- Phase 11 — Emerging player scores (computed during weekly refresh)
-- ===========================================================================
-- One row per (player, league, computed_date). The score is a weighted
-- composite of trend magnitude, consistency, age, and sample size — see
-- docs/analytics/emerging-player-methodology.md for the full formula.
-- Idempotency: re-running for the same computed_date replaces rows.

CREATE TABLE emerging_player_scores (
    id                   SERIAL PRIMARY KEY,
    player_id            INTEGER     NOT NULL REFERENCES players(id),
    league_id            INTEGER     NOT NULL REFERENCES leagues(id),
    computed_date        TIMESTAMPTZ NOT NULL,
    score                DOUBLE PRECISION NOT NULL,           -- 0.0-1.0
    contributing_factors JSONB       NOT NULL DEFAULT '{}',   -- per-factor breakdown for transparency
    UNIQUE (player_id, league_id, computed_date)
);
CREATE INDEX ix_emerging_league_date ON emerging_player_scores (league_id, computed_date);
CREATE INDEX ix_emerging_score ON emerging_player_scores (league_id, computed_date, score DESC);

-- ===========================================================================
-- Phase 13 — Activity tracking, dashboard state, saved players
-- ===========================================================================

-- Activity log: single source of truth for "recently viewed" and user actions.
-- Deduplication is enforced at write time (same entity within 60s = skip).
CREATE TABLE activity_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER     NOT NULL REFERENCES users(id),
    entity_type   VARCHAR(16) NOT NULL,   -- player | team | search | shortlist | report | watch
    entity_id     INTEGER     NOT NULL,
    action_type   VARCHAR(16) NOT NULL,   -- viewed | created | edited | deleted | shared | run
    performed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata      JSONB                        -- context-specific info (e.g. search_definition for "run")
);
CREATE INDEX ix_activity_user_time ON activity_log (user_id, performed_at DESC);
CREATE INDEX ix_activity_entity ON activity_log (user_id, entity_type, entity_id, performed_at DESC);

-- Dashboard state: per-user widget config + dismissed recommendations.
CREATE TABLE dashboard_state (
    id                          SERIAL PRIMARY KEY,
    user_id                     INTEGER NOT NULL REFERENCES users(id),
    widget_config               JSONB    NOT NULL DEFAULT '{}',   -- order/visibility/size per widget
    dismissed_recommendations   JSONB    NOT NULL DEFAULT '[]',   -- [player_id, ...] dismissed for 30 days
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- Saved players: lightweight bookmarks (distinct from Phase 7 shortlists).
CREATE TABLE saved_players (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    saved_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    category  VARCHAR(32),                          -- favorite | prospect | comparison_reference | null
    UNIQUE (user_id, player_id)
);
CREATE INDEX ix_saved_players_user ON saved_players (user_id, saved_at DESC);

-- ===========================================================================
-- Phase 15 — Transfer Intelligence & Market Data
-- ===========================================================================
-- All market data is versioned and append-only (Constitution §3).
-- Valuations carry source attribution and confidence levels.
-- Transfer history is real, confirmed data — never fabricated.

CREATE TYPE market_source AS ENUM ('transfermarkt', 'understat_transfer', 'instat', 'manual');
CREATE TYPE transfer_type AS ENUM ('permanent', 'loan', 'free_agent');
CREATE TYPE transfer_status AS ENUM ('confirmed', 'reported');
CREATE TYPE contract_status AS ENUM ('active', 'expiring_next_season', 'expired', 'on_loan');
CREATE TYPE valuation_confidence AS ENUM ('high', 'medium', 'low');
CREATE TYPE risk_tier AS ENUM ('low', 'medium', 'high');

CREATE TABLE market_valuations (
    id                    SERIAL PRIMARY KEY,
    player_id             INTEGER NOT NULL REFERENCES players(id),
    source                market_source NOT NULL,
    valuation_amount_eur  DOUBLE PRECISION NOT NULL,
    valuation_date        TIMESTAMPTZ NOT NULL,
    low_range             DOUBLE PRECISION,
    high_range            DOUBLE PRECISION,
    confidence_level      valuation_confidence NOT NULL DEFAULT 'medium',
    raw                   JSONB NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (player_id, source, valuation_date)
);
CREATE INDEX ix_market_valuation_player ON market_valuations (player_id, valuation_date DESC);
CREATE INDEX ix_market_valuation_date ON market_valuations (valuation_date);

CREATE TABLE transfer_history (
    id                SERIAL PRIMARY KEY,
    player_id         INTEGER NOT NULL REFERENCES players(id),
    from_team_id      INTEGER REFERENCES teams(id),
    to_team_id        INTEGER NOT NULL REFERENCES teams(id),
    transfer_date     TIMESTAMPTZ NOT NULL,
    reported_fee_eur  DOUBLE PRECISION,
    transfer_type     transfer_type NOT NULL,
    status            transfer_status NOT NULL DEFAULT 'reported',
    source            market_source NOT NULL,
    raw               JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_transfer_player ON transfer_history (player_id);
CREATE INDEX ix_transfer_date ON transfer_history (transfer_date);
CREATE INDEX ix_transfer_to_team ON transfer_history (to_team_id);

CREATE TABLE contract_status (
    id                         SERIAL PRIMARY KEY,
    player_id                  INTEGER NOT NULL REFERENCES players(id),
    current_team_id            INTEGER REFERENCES teams(id),
    contract_end_date          TIMESTAMPTZ,
    contract_value_per_year_eur DOUBLE PRECISION,
    contract_status            contract_status NOT NULL DEFAULT 'active',
    source                     market_source NOT NULL,
    snapshot_date              TIMESTAMPTZ NOT NULL,
    raw                        JSONB NOT NULL DEFAULT '{}',
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (player_id, source, snapshot_date)
);
CREATE INDEX ix_contract_player ON contract_status (player_id);

-- ===========================================================================
-- Phase 16 — Organization / Multi-Tenant Architecture
-- ===========================================================================
-- Design (Multi-Tenant Addendum):
-- * Org membership is opt-in: solo users continue working unchanged.
-- * Every user-owned resource gains optional owner_org_id + visibility.
-- * RBAC enforced at query layer via user_has_permission().
-- * Audit logging captures all team-structure changes.

CREATE TYPE org_role AS ENUM ('owner', 'manager', 'scout', 'viewer');
CREATE TYPE resource_visibility AS ENUM ('personal', 'org_members', 'restricted');
CREATE TYPE org_tier AS ENUM ('free', 'pro', 'enterprise');
CREATE TYPE org_invite_status AS ENUM ('pending', 'accepted', 'expired');
CREATE TYPE audit_action AS ENUM (
    'user_added', 'user_removed', 'role_changed',
    'resource_created', 'resource_shared', 'resource_deleted',
    'comment_added'
);
CREATE TYPE mention_status AS ENUM ('pending', 'read');

CREATE TABLE organizations (
    id                     SERIAL PRIMARY KEY,
    name                   VARCHAR(256) NOT NULL,
    slug                   VARCHAR(128) NOT NULL UNIQUE,
    owner_user_id          INTEGER      NOT NULL REFERENCES users(id),
    tier                   org_tier     NOT NULL DEFAULT 'free',
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    plan_expires_at        TIMESTAMPTZ,
    primary_contact_email  VARCHAR(320),
    billing_contact_email  VARCHAR(320),
    country                VARCHAR(64)
);
CREATE INDEX ix_organizations_slug ON organizations (slug);
CREATE INDEX ix_organizations_owner ON organizations (owner_user_id);

CREATE TABLE org_memberships (
    id                     SERIAL PRIMARY KEY,
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id                INTEGER      NOT NULL REFERENCES users(id),
    role                   org_role     NOT NULL DEFAULT 'scout',
    joined_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    invited_by_user_id     INTEGER      REFERENCES users(id),
    permissions_override    JSONB,
    UNIQUE (org_id, user_id)
);
CREATE INDEX ix_org_memberships_org ON org_memberships (org_id);
CREATE INDEX ix_org_memberships_user ON org_memberships (user_id);

CREATE TABLE org_settings (
    id                     SERIAL PRIMARY KEY,
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    data_retention_days    INTEGER      NOT NULL DEFAULT 90,
    workspace_name         VARCHAR(128),
    enable_audit_logging   BOOLEAN      NOT NULL DEFAULT TRUE,
    allow_public_reporting BOOLEAN      NOT NULL DEFAULT FALSE,
    require_2fa            BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_org_settings_org ON org_settings (org_id);

CREATE TABLE org_invites (
    id                     SERIAL PRIMARY KEY,
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email                  VARCHAR(320) NOT NULL,
    role                   org_role     NOT NULL,
    token_hash             VARCHAR(64)  NOT NULL,
    invited_by_user_id     INTEGER      NOT NULL REFERENCES users(id),
    status                 org_invite_status NOT NULL DEFAULT 'pending',
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at             TIMESTAMPTZ  NOT NULL,
    accepted_at            TIMESTAMPTZ
);
CREATE INDEX ix_org_invites_org ON org_invites (org_id);
CREATE INDEX ix_org_invites_token ON org_invites (token_hash);

CREATE TABLE org_audit_log (
    id                     SERIAL PRIMARY KEY,
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action                 audit_action NOT NULL,
    performed_by_user_id   INTEGER      NOT NULL REFERENCES users(id),
    target_user_id         INTEGER      REFERENCES users(id),
    resource_type          VARCHAR(32),
    resource_id            INTEGER,
    detail                 JSONB        NOT NULL DEFAULT '{}',
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_log_org ON org_audit_log (org_id, created_at);
CREATE INDEX ix_audit_log_performed_by ON org_audit_log (performed_by_user_id);

CREATE TABLE comments (
    id                     SERIAL PRIMARY KEY,
    resource_type          VARCHAR(32)  NOT NULL,
    resource_id            INTEGER      NOT NULL,
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    author_user_id         INTEGER      NOT NULL REFERENCES users(id),
    parent_id              INTEGER      REFERENCES comments(id),
    text                   TEXT         NOT NULL,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now(),
    edited_at              TIMESTAMPTZ,
    deleted_at             TIMESTAMPTZ
);
CREATE INDEX ix_comments_resource ON comments (resource_type, resource_id);
CREATE INDEX ix_comments_org ON comments (org_id, created_at);
CREATE INDEX ix_comments_author ON comments (author_user_id);

CREATE TABLE mentions (
    id                     SERIAL PRIMARY KEY,
    comment_id             INTEGER      NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    mentioned_user_id      INTEGER      NOT NULL REFERENCES users(id),
    org_id                 INTEGER      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    status                 mention_status NOT NULL DEFAULT 'pending',
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_mentions_user ON mentions (mentioned_user_id, status);
CREATE INDEX ix_mentions_comment ON mentions (comment_id);

-- ===========================================================================
-- Phase 17 — Tactical Intelligence (passing networks, heatmaps, formations)
-- ===========================================================================
-- All tactical data is derived from StatsBomb event data.
-- Coverage-gating: only matches with sufficient event data are analyzed.
-- Cached per match to avoid recomputation.

CREATE TABLE match_passing_networks (
    id              SERIAL PRIMARY KEY,
    match_id        VARCHAR(64)  NOT NULL,
    team_id         INTEGER      REFERENCES teams(id),
    phase           VARCHAR(32)  NOT NULL DEFAULT 'full_match',
    network_json    JSONB        NOT NULL,
    metrics_json    JSONB        NOT NULL DEFAULT '{}',
    style_json      JSONB        NOT NULL DEFAULT '{}',
    anomalies_json  JSONB        NOT NULL DEFAULT '[]',
    computed_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (match_id, team_id, phase)
);
CREATE INDEX ix_passing_network_match ON match_passing_networks (match_id);

CREATE TABLE match_spatial_analyses (
    id              SERIAL PRIMARY KEY,
    match_id        VARCHAR(64)  NOT NULL,
    team_id         INTEGER      REFERENCES teams(id),
    analysis_type   VARCHAR(32)  NOT NULL,
    result_json     JSONB        NOT NULL,
    computed_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (match_id, team_id, analysis_type)
);
CREATE INDEX ix_spatial_analysis_match ON match_spatial_analyses (match_id);

CREATE TABLE match_formations (
    id                    SERIAL PRIMARY KEY,
    match_id              VARCHAR(64)  NOT NULL,
    team_id               INTEGER      REFERENCES teams(id),
    detected_formation    VARCHAR(16)  NOT NULL,
    stability_json        JSONB        NOT NULL,
    conformity_json       JSONB,
    computed_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (match_id, team_id)
);
CREATE INDEX ix_formation_match ON match_formations (match_id);

COMMIT;

-- ============================================================================
-- PHASE 16 MIGRATION — Add org ownership columns to existing tables
-- ============================================================================
-- These ALTER TABLE statements add the new columns for multi-tenant support.
-- Safe to run multiple times (IF NOT EXISTS guards).
-- Existing data is unaffected: all new columns default to personal/null.
--
-- Usage:  psql $DATABASE_URL -f app/schema.sql
-- (The CREATE TABLE statements above are idempotent with IF NOT EXISTS
--  on most; the ALTERs below are the migration path for existing DBs.)
-- ============================================================================

BEGIN;

-- Add org ownership columns to shortlists
ALTER TABLE shortlists ADD COLUMN IF NOT EXISTS owner_org_id INTEGER REFERENCES organizations(id);
ALTER TABLE shortlists ADD COLUMN IF NOT EXISTS visibility resource_visibility NOT NULL DEFAULT 'personal';
ALTER TABLE shortlists ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE shortlists ADD COLUMN IF NOT EXISTS restricted_access JSONB;

-- Add org ownership columns to saved_searches
ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS owner_org_id INTEGER REFERENCES organizations(id);
ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS visibility resource_visibility NOT NULL DEFAULT 'personal';
ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id);

-- Add org ownership columns to reports
ALTER TABLE reports ADD COLUMN IF NOT EXISTS owner_org_id INTEGER REFERENCES organizations(id);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS visibility resource_visibility NOT NULL DEFAULT 'personal';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id);

-- Add org ownership columns to watches
ALTER TABLE watches ADD COLUMN IF NOT EXISTS owner_org_id INTEGER REFERENCES organizations(id);
ALTER TABLE watches ADD COLUMN IF NOT EXISTS visibility resource_visibility NOT NULL DEFAULT 'personal';
ALTER TABLE watches ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id);

COMMIT;

-- ===========================================================================
-- Phase 18 — Internal Usage Analytics
-- ===========================================================================
-- Constitution §3: all data is append-only, versioned by timestamp.
-- Constitution §6: no fabricated numbers — events are real, metrics derived.
-- Part E3: raw events retained 90 days, aggregated metrics retained 3 years.

CREATE TABLE analytics_events (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER REFERENCES users(id),
    session_id        VARCHAR(64),
    event_name        VARCHAR(64) NOT NULL,
    event_properties  JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_analytics_event_name_time ON analytics_events (event_name, created_at);
CREATE INDEX ix_analytics_event_user ON analytics_events (user_id, created_at);
CREATE INDEX ix_analytics_event_session ON analytics_events (session_id, created_at);

CREATE TABLE analytics_sessions (
    id                SERIAL PRIMARY KEY,
    session_id        VARCHAR(64) NOT NULL UNIQUE,
    user_id           INTEGER REFERENCES users(id),
    started_at        TIMESTAMPTZ NOT NULL,
    ended_at          TIMESTAMPTZ,
    duration_seconds  INTEGER,
    event_count       INTEGER NOT NULL DEFAULT 0,
    events_json       JSONB NOT NULL DEFAULT '{}',
    device_type       VARCHAR(16),
    browser           VARCHAR(32),
    os                VARCHAR(32)
);
CREATE INDEX ix_session_user_time ON analytics_sessions (user_id, started_at);

CREATE TABLE daily_metrics (
    id                SERIAL PRIMARY KEY,
    metric_date       TIMESTAMPTZ NOT NULL,
    metric_name       VARCHAR(64) NOT NULL,
    tier              VARCHAR(32),
    value             DOUBLE PRECISION NOT NULL,
    computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric_date, metric_name, tier)
);
CREATE INDEX ix_daily_metric_name_date ON daily_metrics (metric_name, metric_date);

CREATE TABLE feature_usage (
    id                      SERIAL PRIMARY KEY,
    usage_date              TIMESTAMPTZ NOT NULL,
    feature_name            VARCHAR(64) NOT NULL,
    adoption_count          INTEGER NOT NULL DEFAULT 0,
    adoption_pct            DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_engagement_minutes  DOUBLE PRECISION NOT NULL DEFAULT 0,
    actions_count           INTEGER NOT NULL DEFAULT 0,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (usage_date, feature_name)
);
CREATE INDEX ix_feature_usage_date ON feature_usage (usage_date);

CREATE TABLE cohort_retention (
    id                      SERIAL PRIMARY KEY,
    cohort_month            TIMESTAMPTZ NOT NULL,
    months_since_signup     INTEGER NOT NULL,
    cohort_size             INTEGER NOT NULL,
    retained_count          INTEGER NOT NULL,
    retention_pct           DOUBLE PRECISION NOT NULL,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (cohort_month, months_since_signup)
);
CREATE INDEX ix_cohort_retention_month ON cohort_retention (cohort_month);

CREATE TABLE analytics_alerts (
    id                SERIAL PRIMARY KEY,
    alert_name        VARCHAR(64) NOT NULL,
    metric_name       VARCHAR(64) NOT NULL,
    threshold_type    VARCHAR(32) NOT NULL,
    threshold_value   DOUBLE PRECISION NOT NULL,
    actual_value      DOUBLE PRECISION NOT NULL,
    message           TEXT NOT NULL,
    fired_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at   TIMESTAMPTZ
);
CREATE INDEX ix_alert_fired ON analytics_alerts (fired_at);
CREATE INDEX ix_alert_name ON analytics_alerts (alert_name);

CREATE TABLE analytics_access_log (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users(id),
    dashboard_name    VARCHAR(64) NOT NULL,
    query_params      JSONB,
    accessed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_access_log_user ON analytics_access_log (user_id, accessed_at);
