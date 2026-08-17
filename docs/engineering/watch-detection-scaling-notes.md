# Watch-trigger detection — scaling notes

*Phase 10 (Part F2). Status: implemented at MVP scale with the batching
strategy already in place; further optimization documented for post-launch
growth.*

## The problem

`detect_watch_triggers` (app/watch/detection.py) evaluates every active watch
against the freshly-published weekly snapshot. The naive implementation is one
query per watch — for a player history, a team season list, league coverage,
and anomaly counts — which becomes N×4 queries as the watch table grows.

## What's implemented now

The job already avoids the per-watch query explosion:

- **Player histories**: `_player_history` loads the two most recent published
  snapshot dates for ALL watched players in ONE distinct-query, then their
  percentile rows in a second `IN` query — 2 queries total, regardless of watch
  count.
- **Team seasons**: one query for all watched teams.
- **League coverage**: one query for all leagues involved.
- **Anomaly counts**: one joined query for all watched players on the cycle's
  snapshot date.

Trigger evaluation itself is then pure in-memory work over the batch results.

## Why that's sufficient at MVP scale

At the launch-era scale (thousands of watches, ~15 leagues), the batch queries
above keep the whole detection step in the low-single-digit-milliseconds range
per thousand watches — far below the weekly cadence's budget. The percentile
rows for two dates × watched players is the largest fetch; each row is small
(a metric name + value), so even 10k watches × 16 metrics × 2 dates is
~320k small rows, readable in well under a second.

## The scaling path if watch count grows by orders of magnitude

If the watch table reaches hundreds of thousands of rows (or detection must
run more frequently than weekly), the following are the documented next steps,
in order of cost/benefit:

1. **Snapshot-pair materialization**: instead of joining percentile rows on
   every detection run, maintain a `watch_snapshot_pairs` cache table keyed on
   (watch_id, snapshot_date) holding the pair of percentile vectors needed for
   comparison. Detection then reads one row per watch instead of two joined
   queries. Invalidated automatically when a new snapshot is published.
2. **Partitioned percentile reads**: the two-date percentile fetch can be
   pushed down further with an index on `(stat_snapshot_id, metric_name)` +
   `is_published` — already effectively covered by existing indexes; revisit
   with a composite index on (player_id, scrape_date) for the dates query.
3. **Worker parallelism**: the evaluation loop is embarrassingly parallel —
   shard watches by `entity_id % N` across N workers, each with its own
   session, then merge `WatchDetectionReport` counts. Only the alert inserts
   need the shared uniqueness guarantee, which the (watch_id, alert_type,
   dedupe_key) unique constraint already provides regardless of which worker
   wins the insert.
4. **Incremental trigger evaluation**: only watches whose entity appears in
   the *changed* set (players whose new snapshot differs from the previous one
   in any metric, team, or season) need re-evaluation. The changed set can be
   computed once per refresh from the ingested records, skipping the majority
   of watches whose entity didn't change at all.

## Idempotency and correctness invariants (must survive any optimization)

- Re-running detection for an already-processed snapshot date creates no
  duplicate alert rows — the (watch_id, alert_type, dedupe_key) unique
  constraint is the hard guarantee; any optimization must keep it.
- The club-change trigger fires once per transfer transition (keyed on the
  from/to/snapshot triple), never once per subsequent weekly snapshot.
- `detail` values in every alert remain traceable to the real snapshot,
  coverage, or anomaly rows that triggered it.
