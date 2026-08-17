# Alert trigger definitions — what counts as alert-worthy (Phase 10)

*This document is the specification the detection job implements against. Every
threshold is explicit and every decision is stated — a vague trigger definition
would be exactly the kind of unexplained magic number the Constitution forbids
for any user-facing claim.*

The central design problem of this phase is **noise-avoidance**: a watchlist
that fires on every half-point percentile shift trains users to ignore it.
Nothing in this document is a sensitivity knob picked ad hoc; each threshold is
the smallest value that survives snapshot-to-snapshot noise in the underlying
data (percentile ranks are recomputed from scratch each weekly cycle over the
same cohort, so ±5 points of rank churn is ordinary, while a 15-point move is
a real, visible change in a player's standing).

---

## 1. Followable entities

- **Players** (primary) and **Teams** (secondary) — both are first-class from
  the start. `watches.entity_type` is an enum (`player` | `team`); every
  trigger type that applies to players also applies to teams where the signal
  exists (a team has no percentile vector, so percentile-movement triggers are
  player-only by construction — this is stated, not implied).

## 2. Trigger types — exact definitions

### 2.1 `percentile_movement` (players only)

**Trigger condition:** a watched player's percentile value for a metric changes
by **≥ 15 percentile points** (inclusive) between the two most recent
consecutive **published** snapshots, AND the player qualifies (≥ the
registry's `qualifying_minutes`, 900) in **both** snapshots.

- The threshold is a deployment-config value: `ALERT_PERCENTILE_MOVE_THRESHOLD`
  (default `15`), read through `app/config.py` — tunable post-launch from real
  alert-volume data without a code change.
- **Boundary semantics (explicit):** movement of exactly 15.0 points **fires**
  (`>=`); 14.9 does not. The inclusive boundary is chosen because the
  comparison is exact (percentile values are stored as floats from the same
  computation), so there is no rounding ambiguity to hedge against.
- **Which metrics are watched:** by default, every metric in the entity's
  position-group metric set from the Metric Registry (the same set the Radar
  tool renders). If the watch has `followed_metrics` set (Part A4 refinement),
  only those metrics are evaluated. `si_index` is **not** a trigger metric —
  it is a composite of the metric percentiles; alerting on the composite and
  its components would double-report the same underlying change.
- **Which snapshot rows are compared:** the winning `percentile_snapshots` rows
  (published, `is_published = True`) for the metric across the two most recent
  distinct snapshot dates. If the metric's percentile row is missing for either
  snapshot, that metric produces no alert that cycle (a player cannot be
  evaluated on data that doesn't exist — the Phase 6/8 missing-data rule).
- **Cohort honesty:** percentiles are cohort-relative (position × league tier ×
  season). A player whose cohort changed (transfer between leagues) has a
  legitimate percentile jump that is still a *real* change in their published
  standing; the alert's `detail` carries both snapshots' cohort labels so the
  reader can see the comparison context.

**Detail payload (every value traceable to `percentile_snapshots`):**

```json
{
  "metric": "si_prgp_p90",
  "metric_name": "Progressive passes per 90",
  "from_percentile": 62,
  "to_percentile": 81,
  "from_snapshot_date": "2026-08-05",
  "to_snapshot_date": "2026-08-12",
  "from_minutes": 1234,
  "to_minutes": 1480,
  "from_league": "Premier League",
  "to_league": "Premier League"
}
```

### 2.2 `club_change` (players)

**Trigger condition:** `stat_snapshots.team_id` differs between the two most
recent consecutive published snapshots for a watched player.

- This reuses the **same signal** Phase 3's trend-chart transfer annotation
  uses (`team_id` change across consecutive snapshots). The detection is
  extracted into a shared helper so the two features cannot drift apart.
- **Fires once per transition, not once per week at the new club:** the alert
  is keyed on the (from_team, to_team, to_snapshot_date) triple. On the next
  weekly cycle, the player's two most recent snapshots both have the new
  team_id — no change, no alert. A subsequent transfer fires a new alert.

**Detail payload:**

```json
{
  "from_team": "Brighton",
  "from_team_id": 17,
  "to_team": "Arsenal",
  "to_team_id": 9,
  "snapshot_date": "2026-08-12",
  "from_league": "Premier League",
  "to_league": "Premier League"
}
```

### 2.3 `new_season_data` (players and teams)

**Trigger condition:** the entity's newest published snapshot has a season
different from its previous published snapshot's season AND that newest
snapshot meets the qualification floor (players) or is the team's first
snapshot of the season (teams).

- Fires **once per season per entity** (keyed on `entity + season`), matching
  the "structural event, not statistical" definition — a season rollover is a
  single event, not a weekly one.
- For players this is the *first qualifying snapshot* of the new season: the
  new-season snapshot must meet the floor, so a player who appears in week one
  below the floor is not alerted until their snapshot qualifies (the honest
  threshold — an unqualified snapshot carries no published percentile data to
  report on).

**Detail payload:**

```json
{
  "new_season": "2026-27",
  "previous_season": "2025-26",
  "snapshot_date": "2026-08-19",
  "entity_type": "player",
  "entity_name": "Erling Haaland"
}
```

### 2.4 `data_coverage_change` (players and teams — the Statlas honesty trigger)

Two sub-signals, both read from Phase 1 tables (no parallel detection):

- **`coverage_gained`:** the entity's league gains shot/pass-map coverage for
  the current season — a `data_coverage` row with `source = 'statsbomb'` for
  the entity's league + season appears where the watch previously had no such
  coverage. Keyed on `(league, season)` so it fires once when the coverage row
  first lands, not on every refresh.
- **`source_anomaly`:** an `ingestion_anomalies` row was created for the
  entity's snapshots during this cycle (anomaly check flagged values — the
  source may be providing bad data). Keyed on `(entity, snapshot_date)` so a
  player whose data stays flagged across cycles alerts once per cycle while the
  problem is unresolved, and stops the moment the anomaly is resolved and no
  new one is flagged.

**Detail payload:**

```json
{
  "signal": "coverage_gained",
  "league": "Premier League",
  "season": "2025-26",
  "coverage_source": "statsbomb",
  "entity_type": "player",
  "entity_name": "Bukayo Saka"
}
```

### 2.5 `condition_entered` — explicitly scoped as a v2 enhancement, NOT in v1

Attaching a Phase 8 structured condition to a watch ("alert me if any CM I'm
not tracking crosses the 80th percentile in progressive passes") is genuinely
valuable but adds a second evaluation surface (per-condition evaluation across
the *unfollowed* population, not just per-entity diffs). This phase keeps the
per-entity diff model coherent; condition-based watches are documented as a
v2 enhancement reusing `execute_structured_query`'s evaluation, mirroring how
Phase 8 shipped AND-only and scoped OR/grouping. **v1 ships 2.1–2.4 only.**

## 3. Explicit non-triggers (things that do NOT alert)

| Situation | Why it does not alert |
|---|---|
| Percentile movement below 15 points | Snapshot-to-snapshot rank churn in a recomputed cohort; alerting on it is noise |
| Movement on a metric outside `followed_metrics` (when set) | The user narrowed their watch; broad movement is not what they asked to see |
| The same club change across subsequent cycles | Keyed on the transition; the player being at the new club is not a change |
| A player below the qualification floor in either compared snapshot | Below-floor snapshots carry no published percentile data; there is nothing real to report |
| Movement of the Statlas Index | Composite metric; would double-report component movement |
| A metric missing a published percentile in either snapshot | Same missing-data rule as Phases 6/8 — never guess |
| Duplicate detection of the same transition | Idempotent via dedupe keys; re-running detection for a processed snapshot-date creates nothing |

## 4. Follow granularity — the scoping decision

**v1: broad by default, per-metric as an explicit refinement.** A follow
watches "any significant movement across the entity's metric set" (players) or
"any structural event" (teams). `watches.followed_metrics` (nullable JSON
array) narrows a player watch to specific metrics — a filter on the same
detection, not a second system. This mirrors Phase 8 shipping AND-only first
and flagging grouped logic as a future enhancement. Per-metric refinement is
implemented in v1 because it is a one-line filter; the *generalized*
condition-watch (2.5) is the deferred piece.

## 5. Delivery model — digest-first

Weekly-refresh-driven alerts are naturally batched. `notification_preferences.
digest_frequency` is `immediate | daily_digest | weekly_digest` (default
`immediate`). Because the detection job runs once per weekly refresh, an
`immediate` user receives at most one alert email per refresh anyway; digest
modes additionally batch across *refresh* boundaries (a user who hasn't checked
in for three weeks gets one weekly digest, not three emails). See
`docs/product/notification-delivery.md` for the delivery contract.
