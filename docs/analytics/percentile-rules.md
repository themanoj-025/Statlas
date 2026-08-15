# Statlas Percentile Rules

*Phase 0 deliverable A2. Specifies how percentile values — and therefore Statlas Index scores, which are weighted averages of percentiles — are grouped, recomputed, and preserved over time. Implements Constitution §3 (versioned snapshots, append-only data, recency labeling) and §6 items 11–12.*

*Related documents: `methodology.md` (the index formula that consumes these percentiles) · `data-compliance-notes.md`.*

---

## 1. Grouping — where a percentile is computed

Every percentile is computed within the intersection of exactly three dimensions:

```
{ season } × { position group } × { league tier }
```

### 1.1 Why not per-league?

**Per-league percentiles are the most precise within a league but make cross-league comparison actively misleading.** A player ranked at the 80th percentile for tackles among Premier League centre-backs and another at the 80th among Eredivisie centre-backs would read as equals, when the two pools are not equal in quality. Statlas exists to support cross-league comparison (scouting, media, agents), so per-league grouping fails the product's core use case.

### 1.2 Why not global?

**Global percentiles solve cross-league comparison but flatten quality.** A single global pool of, say, 2,000 centre-backs across twenty leagues would be dominated by volume from weaker leagues; a Tier 1 player's percentile would be inflated by the tail of low-quality peers, and two players of genuinely different quality could land on the same percentile. Global also breaks when coverage is partial (see below).

### 1.3 The chosen grouping: league tier

Percentiles are computed **within league tier**, which is the defensible middle:

- **Tier 1** — Big-5 first divisions: English Premier League, Spanish La Liga, Italian Serie A, German Bundesliga, French Ligue 1.
- **Tier 2** — Eredivisie, Primeira Liga, Belgian Pro League, Süper Lig, Scottish Premiership, Austrian Bundesliga, Swiss Super League, Greek Super League, Danish Superliga.
- **Tier 3** — Big-5 second divisions (Championship, LaLiga 2, Serie B, 2. Bundesliga, Ligue 2) and further leagues as added to the data coverage matrix.

The tradeoff, stated plainly: **a Tier 1 percentile and a Tier 2 percentile are not directly comparable** (the Tier 1 pool is stronger), but within a tier, cross-league comparison is meaningful — which is the comparison the product actually makes. The UI labels every percentile with its tier ("87th percentile · Tier 1 · ST"), so the limit is visible rather than silent.

### 1.4 Consequences of partial coverage

MVP coverage is Tier 1 in full (per the data coverage matrix). Percentiles are only computed when the pool is **complete for its tier**: if a tier's league list is partially ingested, percentiles for that tier are not published until all leagues in the tier are present for the season. This prevents a half-populated pool from silently shifting every percentile. The coverage matrix is the arbiter (Constitution §3).

### 1.5 xG model consistency

Because percentiles group by tier, and because Understat covers all of Tier 1 and none of Tier 2/3, **Tier 1 xG/xA inputs use the Understat model and Tier 2/3 use FBref's Opta model** (see `methodology.md` §2.3). A model change for a tier invalidates old percentile values for that tier — handled as a new snapshot with a changelog entry, never a silent reflow.

### 1.6 Position group

Position groups are the eight outfield groups plus GK defined in `methodology.md` §3, assigned from FBref `Pos` codes with a review-log for ambiguous cases.

---

## 2. Minimum pool size

A percentile is **not computed** when the qualifying pool (players meeting the 900-minute threshold in the group) is smaller than **30 players**. Below that, the standard error of a percentile rank makes the comparison meaningless. The group shows the explicit state:

> "Not enough qualifying players in this group yet this season — percentiles resume when 30 players pass the 900-minute threshold."

This copy appears in the UI; it is not a debug message.

---

## 3. Recalculation cadence

- **Data refresh:** every **Wednesday, 03:00 UTC** the pipeline ingests the previous match week (per league calendar; see data pipeline phase for schedule details).
- **Recalculation:** percentiles and index scores are recomputed **immediately after each successful refresh**, synchronously, as one transactional job. There is no separate, decoupled "percentile cron" that can run against a half-refreshed database.
- **If the refresh fails**, the percentiles from the last successful snapshot remain published, and the recency label continues to show the last snapshot date. Percentiles are never recomputed against partially-refreshed data.
- **Display:** every percentile and index value carries `percentile as of <snapshot date>` where the snapshot date is the data date of the underlying refresh. This is the recency label mandated by Constitution §3.

---

## 4. Historical immutability — past percentiles never change

The Constitution requires versioned snapshots and append-only history (§3, §6-11). The percentile rules implement it strictly:

1. **Each recomputation writes a new snapshot row set**, keyed by `(player_id, season, position_group, league_tier, metric_id, snapshot_date)`, with the computed percentile and the `computed_on` timestamp. Nothing is updated in place.
2. **A player's "current" percentile is the latest snapshot** whose `snapshot_date` is on or before today. The UI may show a history toggle of prior snapshots' values.
3. **When a new snapshot lands, previous snapshot rows remain byte-identical.** No backfill, no reflow, no "correction" of history. If a source publishes a corrected value (e.g., FBref fixes a scorer), the correction enters as a **new snapshot** — it never mutates the old one. The old value stays queryable and the changelog records the correction.
4. **A percentile seen on a past date is always verifiable** against the snapshot row for that date. This is what makes the product's "as of" labeling honest.

### 4.1 Why immutability matters here

Percentiles are *relative* values: they shift as the pool shifts. If we silently reflowed history, a scout's saved comparison from two weeks ago would change under them with no record. Immutability turns "the number changed" into "a new snapshot exists," which is auditable, and it is the difference between an analytics product and a black box.

---

## 5. Special cases

### 5.1 Ties

Ties share the **midpoint** percentile (fractional-rank method; `methodology.md` §5). Two players with identical values get identical percentiles; the reported value is the honest midpoint of the tied block.

### 5.2 Mid-season transfer across tiers

Percentile grouping uses the **tier of the player's club at the snapshot date**. A January transfer from a Tier 1 league to a Tier 2 league produces two series in the same season (Tier 1 snapshots before the transfer, Tier 2 after), each labelled with its tier and the club at that date. Neither series is recomputed retroactively. This is the honest representation of "his percentile moved because his peer group changed."

### 5.3 League tier changes between seasons

Tier assignments are fixed per season (e.g., a club promoted into Tier 1 plays a Tier 1 season). Tier lists are reviewed once per summer and changes ship as a changelog entry before the first snapshot of the new season.

### 5.4 Below-threshold players

Players under 900 minutes show "pending qualification — needs X more minutes" and are **excluded from peer pools** (a player can rank peers without being ranked themselves). This keeps pool sizes honest early in a season.

---

## 6. Versioning

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-11 | Initial spec: tier-based grouping (Tier 1/2/3 lists), minimum pool of 30, weekly Wednesday 03:00 UTC recalc, immutable snapshot series, transfer/tier-change edge cases. |
