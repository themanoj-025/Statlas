-- ============================================================================
-- STATLAS — MIGRATION 001: percentile_snapshots unique key gains the tier dimension
-- Closeout C1 (tier-completeness gate / cross-tier transfer fix)
--
-- Why: a same-season cross-tier transfer produces two qualifying stat_snapshots
-- for one player (one per league/tier). With the old key
--   UNIQUE (stat_snapshot_id, metric_name)
-- the same stat_snapshot could only carry percentile rows for ONE tier —
-- computing the other tier's cohort would raise a unique-key collision
-- (the documented "fails loudly today" behavior). The percentile job now
-- resolves source precedence PER TIER, so a snapshot's rows must be keyed by
-- (stat_snapshot_id, metric_name, league_tier) to be insertable for each tier.
--
-- Applies to PostgreSQL databases created before the closeout (schema.sql is
-- the canonical DDL for fresh volumes; this is the upgrade path for existing
-- volumes). Run with:  psql $DATABASE_URL -f scripts/migrations/001_percentile_tier_key.sql
-- Idempotent: the constraint is dropped + re-added, so re-running is safe.
-- ============================================================================

BEGIN;

ALTER TABLE percentile_snapshots
    DROP CONSTRAINT IF EXISTS uq_percentile_snapshot_metric;

ALTER TABLE percentile_snapshots
    ADD CONSTRAINT uq_percentile_snapshot_metric_tier
    UNIQUE (stat_snapshot_id, metric_name, league_tier);

COMMIT;
