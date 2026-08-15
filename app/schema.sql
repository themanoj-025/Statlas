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

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    plan          plan         NOT NULL DEFAULT 'free',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
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

COMMIT;
