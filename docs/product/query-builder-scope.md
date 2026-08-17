# Structured Query Builder — Scope & Grammar (Phase 8)

This document defines the structured search feature: the condition grammar,
the execution semantics (qualification floor, missing-data handling), the
deliberately-scoped logic model, and the persistence rules. Everything here
is enforced in `app/queries/structured_search.py` and covered by tests in
`tests/test_structured_search.py`.

## 1. The query definition

A query is a JSON object with a small fixed shape:

```json
{
  "position_group": "CM",            // or null (any position group)
  "league_tier": "tier_1",           // or null (any tier)
  "age_max": 23,                     // or null (no age cap)
  "conditions": [
    { "metric": "si_prgp_p90", "operator": "percentile_gte", "value": 75 },
    { "metric": "si_tkl_p90",  "operator": "percentile_gte", "value": 60 },
    { "metric": "minutes_played", "operator": "gte", "value": 1500 }
  ],
  "condition_logic": "AND"
}
```

- `position_group` / `league_tier` / `age_max` are scalar filters; `age_max`
  is sugar for a raw `age ≤ N` condition (age computed at the player's latest
  snapshot date — the "Data as of" date — so it is deterministic and honest).
- `conditions` is the list of metric conditions. Each condition has:
  - `metric`: a canonical Metric Registry id, or the special id
    `minutes_played` (raw per-90 registry metrics come from
    `stat_snapshots.raw_stats`, keyed by registry id).
  - `operator`: percentile operators for registry metrics
    (`percentile_gte`, `percentile_lte`, `percentile_between`) and raw
    operators (`gte`, `lte`, `between`, `eq` — `eq` is meaningful for
    `minutes_played` and integer values; raw float equality is rarely useful
    but allowed).
  - `value` (+ `value_max` for `between` operators).
- `condition_logic`: **only `"AND"` is supported in v1.** See §2.

Percentile conditions are relative to the player's own cohort
({season, position group, league tier}) — the percentile value stored in
`percentile_snapshots` is used as-is, exactly the value the profile page
displays. Raw conditions use literal values (minutes, age, per-90 numbers).
The UI marks the two types visually (`p75+` style percentile labels vs
literal `1,500 min`), because mixing them without distinction would confuse
what the query is actually filtering on.

## 2. Logic model: AND-only, up to 8 conditions

v1 supports **AND only**, with a hard maximum of **8 conditions**. Rationale:

- AND is the scout's dominant real pattern ("a player who does *all* of these
  things"), it maps 1:1 to SQL, and its results are easy to reason about.
  OR/grouped logic is meaningfully more complex to build *correctly*
  (grouping, precedence, UI representation) and to explain honestly in the
  results view.
- Shipping half-correct grouped logic would violate the phase's own core
  rule: an incorrectly-executed condition returning wrong players is a
  data-integrity failure. AND-only is small and provably correct.
- **Scoped future enhancement:** OR and nested groups (with precedence rules
  and a documented evaluation order) are tracked as a future phase; the
  grammar reserves the `condition_logic` field so the model doesn't change
  shape when it lands. The validator rejects anything but `"AND"` with a
  specific message, not a silent reinterpretation.

## 3. Execution semantics

### 3.1 Population and the always-applied qualification floor

Every query runs against the **published population** (the same
`is_published = true` gate every leaderboard uses) for the **latest season**
with data, at the **latest snapshot date** in that season — i.e., the
"current" percentile set the whole product serves.

The **900-minute qualification floor (`qualifying_minutes` in the Metric
Registry) is always applied, even when the user's query contains no minutes
condition.** A query may not silently surface statistically-unreliable
players just because the user didn't think to filter minutes. The floor is a
separate, always-on constraint, documented in the UI ("every result has
≥ 900 league minutes") — distinct from any user-specified minutes condition.

### 3.2 Missing data — exclusion, never ambiguity

If a player is missing a published percentile for a metric used in a
percentile condition, or missing the raw value for a raw metric condition,
**that player is excluded** — a player cannot satisfy a condition on data
that does not exist for them. The response carries an explicit note:
"Results reflect only players with complete data for every selected metric."
No zero-imputation, no average-fill, no silent inclusion.

### 3.3 Condition execution

Percentile conditions read `percentile_snapshots.percentile_value` for the
player's latest snapshot (published). Raw conditions read
`stat_snapshots.minutes_played`, the player's age at the snapshot date
(from `date_of_birth`), or `stat_snapshots.raw_stats[metric_id]` for
registry metrics. All conditions AND together.

### 3.4 Ranking

Default sort: **Statlas Index descending** (the published index row). Users
may sort by minutes, age, name, or any condition metric (percentile or raw),
with direction aware of the metric's `lower_is_better` flag (mirroring the
leaderboard's sort semantics).

### 3.5 Diagnostics (empty-result guidance)

The execution pass already computes each condition's individual pass count
(the same per-player values feed all conditions), so when `total == 0` the
response can name the **most restrictive condition** — the one with the
smallest individual pass count — at zero extra query cost. The UI surfaces
it ("0 players match — try lowering the progressive-passes threshold"), per
the phase's specific-not-vague copy standard.

## 4. Persistence

- **`saved_searches`**: user-owned; name, description, query_definition
  (the JSON above), created/updated timestamps, `last_run_at`. A run
  re-executes against *current* data — weekly refreshes mean results can
  differ from when the query was saved; the UI states this explicitly
  ("Results reflect the latest weekly refresh, which may differ from when
  this search was saved").
- **`search_history`**: every executed query for signed-in users is logged
  automatically (the live builder preview passes `log_history=false`, so
  typing in the builder does not spam history). **Retention cap: the newest
  50 entries per user** — on insert, older entries are deleted. Documented,
  bounded, never unbounded.
- **`search_presets`**: Statlas-authored curated queries, stored in
  `app/config/search_presets.json` (methodology-as-code precedent, not
  user-owned data); public — no auth required to list them.
- **Tier gating**: Free = up to **5 saved searches** (`saved_searches_max`
  in pricing.json); Pro/API-Business unlimited. The cap raises the same
  `WorkspaceLimitExceeded`-style honest upsell as Phase 7's shortlist cap
  (consistent wording, never a generic error).

## 5. Authorization

Saved searches and history are per-user data with the **exact Phase 7
ownership pattern**: every read/write verifies the requesting user owns the
row, and a missing OR foreign id returns 404 (never a 403 that leaks
existence). Presets are public and unowned.
