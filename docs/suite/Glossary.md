# Glossary.md — Statlas Shared Vocabulary

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-14 |
| Owner | TPM |
| Status | In Review |

One definition per term, used identically in every doc in this suite. If you need a new term, add it here first.

| Term | Definition |
|---|---|
| **Alias** | A source-specific name spelling for a player (`player_name_aliases`), e.g. FBref's "Mohamed Salah". Drives alias-aware search (US-001). |
| **Big-5 / top-5** | The top-5 European leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) — tier value `top-5`. |
| **Cohort** | The peer group a player is ranked within: position_group × league_tier (per percentile-rules.md). |
| **Coverage gate** | The rule that UI features (shot maps, event data) render only when `data_coverage` confirms the source has the data — never imply coverage that doesn't exist (REQ-012). |
| **data_coverage** | Table/API of which (league, source) pairs have which seasons + scrape health (`active/stale/failed`). |
| **Dataset mode** | `fixture-demo` vs `production` (`STATLAS_DATASET_MODE`). The honest label; production flip is blocked on RISK-01. |
| **Fixture-demo** | The labeled demo dataset seeded through the real pipeline (`scripts/seed_dev_db.py`). Not production data. |
| **Index score / Statlas Index** | The 0–100 composite metric: weighted sum of per-90 percentiles within position group × league tier, computed only for players ≥ 900 minutes. Formula public on /methodology (REQ-015). |
| **Leaderboard** | Sortable/filterable/paginated table of players by metric/percentile/index (REQ-013). |
| **Metric id** | Canonical key for a per-90 stat, e.g. `si_gls_p90`, `si_prgp_p90` (16 in `metric_registry.json`). |
| **Minutes threshold** | 900 league minutes required for an index score (methodology.md justification; `qualifying_minutes` in registry). |
| **PAdj** | Pace-adjusted statistic (FBref-derived). Always defined on the axis tooltip (REQ-003). |
| **Percentile** | Rank of a player's metric value within their cohort, 0–100 (per-league-tier grouping, immutable history). |
| **Publish gate** | The rule that a computation run's results are queryable only after anomaly checks pass/are resolved. |
| **Qualifying player** | A player meeting the 900-minute floor (has index score). Below it → "pending qualification — needs X more minutes". |
| **Radar tool** | The core /compare experience: 1–4 player overlay, percentile ↔ per-90 toggle, per-axis definitions (REQ-001–005). |
| **Recency** | The labeled scrape date / qualifying season shown on profiles so users know data freshness (US-007). |
| **Snapshot** | One versioned row of a player's raw stats for a (season, source, scrape_date) — immutable (`stat_snapshots`). |
| **Similar players** | Nearest-neighbor ranking over percentile vectors within a position group, with stated basis (REQ-006). |
| **Tier** | League quality class: `top-5` / `second-tier` / `other`. Grouping dimension for percentiles (percentile-rules.md). |
| **Weekly refresh** | The orchestrated job: scrape → reconcile → anomaly-check → percentile-compute → index-compute → mark-published (idempotent). |
| **WCAG 2.1 AA** | Accessibility compliance target; enforced via axe CI (0 violations) on core pages. |

## Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Terms used in REQs |
| [TechSpec.md](TechSpec.md) | Technical terms cross-ref |
| [AppFlow.md](AppFlow.md) | Screen-level terms |
| [Design.md](Design.md) | Design tokens/terms |
| [Schema.md](Schema.md) | Table-level terms |
| [ImplementationPlan.md](ImplementationPlan.md) | Task terms |
| [Tracker.md](Tracker.md) | Status terms |
| [Rules.md](Rules.md) | Rule terms |
| [API.md](API.md) | Payload terms |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | Compliance terms |
| [Testing.md](Testing.md) | Test terms |
| [Deployment.md](Deployment.md) | Env terms |
| [RiskRegister.md](RiskRegister.md) | Risk terms |
