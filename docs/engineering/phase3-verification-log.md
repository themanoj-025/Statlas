# Statlas — Phase 3 Verification Log (2026-08-14)

Date: 2026-08-14 · Scope: Phase 3 execution prompt (Differentiators: Trend Charts, Shot/Pass Maps, Sharing) audited against the codebase at commit `64651b7`.
Method: every Part A–D requirement from the Phase 3 prompt re-verified against live code, query layer, component implementations, unit tests, and the e2e suite (`web/e2e/phase3.spec.ts`, CI run `31806249020` — all 5 jobs green, 15/15 e2e passing on GitHub Actions).
Constitution baseline: `docs/CONSTITUTION.md` (data-honesty rules, Never-List, §7 Definition of Done) — every item below was checked against it, with zero violations found.

---

## Part A — Trend / Time-Series Charts

| Req | Requirement | Evidence | Status |
|---|---|---|---|
| A1-a | State the actual granularity — never imply per-match precision | `app/queries/trend_queries.py:40` `GRANULARITY_NOTE` ("snapshot granularity, not per-match data"); response carries `granularity: "snapshot"`; `TrendChart` renders the note in the UI | ✅ |
| A1-b | Rolling-window computation (configurable 5/10) from versioned `stat_snapshots` | `TREND_WINDOWS = (5, 10)`, `DEFAULT_WINDOW = 5` (`trend_queries.py:34-35`); reads only `StatSnapshot` (append-only) — the payoff of Phase 1's immutable snapshots | ✅ |
| A1-c | Handle gaps explicitly — dashed segment / break, never interpolation | `trend_queries.py` marks `gap_after` + `gap_ranges` when a cohort-calendar date is missing; `TrendChart.tsx:289` renders `trend-line--gap` dashed paths + explicit break markers + "gap" labels | ✅ |
| A1-d | Anomaly-flagged snapshots surfaced | `trend_queries.py` sets `anomaly=true` from unresolved `ingestion_anomalies`; `TrendChart.tsx` draws a warning ring on flagged points | ✅ |
| A2-a | Line/area chart, x = snapshot date, y = value; raw + percentile modes | `TrendChart.tsx`; `TrendMode = "pct" \| "raw"`; pct pins axis to 0–100, raw scales to displayed max (verified in `web/lib/chartSvg.test.ts:42,84`) | ✅ |
| A2-b | Multi-metric overlay with legend + accessible color differentiation | `TrendTool` metric chips (multi-select), one line per player × metric, dash pattern per metric (`METRIC_DASHES`), named legend below chart; numbers always accompany lines (`trend-end-label`) — never colour alone | ✅ |
| A2-c | Multi-player overlay (up to 3) — feature DataMB lacks | `MAX_TREND_PLAYERS = 3` (`web/lib/share.ts:38`), enforced in `TrendTool.tsx:149` with an explicit at-limit message (`TrendTool.tsx:263`) | ✅ |
| A2-d | Annotate significant events derived from real data (transfer from `team_id` change) | `trend_queries.py` derives `events` from consecutive-snapshot `team_id` changes; `TrendChart` renders "Timeline" note. Test: `tests/test_trend.py:137 test_transfer_annotation_derived_from_team_change` | ✅ |
| A3 | Loading / insufficient-history / error states | Skeleton is a real line-chart shape (`trend-skeleton`, `TrendChart.tsx`); insufficient history states "N of 5 minimum snapshots available" (`MIN_TREND_SNAPSHOTS = 5`, `insufficient` flag, verified `tests/test_trend.py:123`); error state has Retry (`TrendChart` `onRetry` wired in `TrendTool`) | ✅ |

**Part A tests:** `tests/test_trend.py` — gap-not-interpolated, rolling window keeps last N, insufficient-history honesty, transfer annotation, published-rows-only percentiles, anomaly marking, validation/missing-player (7 tests).

---

## Part B — Shot Maps and Pass Maps

| Req | Requirement | Evidence | Status |
|---|---|---|---|
| B1 | Coverage-gating FIRST: query `data_coverage`; entry point renders only with confirmed coverage | `EventMaps.tsx` — coverage check is the first step (`api.playerEventCoverage`); the map section renders only when `coverage.has_coverage`; the component never fetches events outside the matrix | ✅ |
| B1-test | Automated test that maps never render without coverage | `tests/test_event_queries.py:91 test_coverage_gating_without_coverage_row_never_renders`, `:109` active-row unlocks, `:142` failed-status blocks | ✅ |
| B2-a | Accurate pitch diagram with shot locations sized/colored by xG | `Pitch.tsx` (soccer → pitch coordinate mapping, accurate proportions) + `ShotMap.tsx`; marker radius scales with xG (`2.2 + 4.2 * min(1, xg/0.6)`); null xG keeps fixed size — no invented precision | ✅ |
| B2-b | Outcome via shape AND colour (never colour alone) | `ShotMap.tsx` `OUTCOME_COLORS` + shape mapping: Goal = filled circle, Saved = diamond, Blocked = triangle, Off Target = square; legend renders shape glyph + label + count (`role="list"` "Shot outcomes") | ✅ |
| B2-c | Filterable by match / competition / season, bounded to confirmed coverage | `ShotMap`/`PassMap` filter UI bounded to `coverage.competitions`; no competition option outside the coverage matrix | ✅ |
| B2-d | Accessible data-table fallback (a pitch alone is not accessible) | `ShotMap.tsx` "Show data table" toggle → structured `<table aria-label="Shots for {player}">` with minute/outcome/xG rows; `PassMap` likewise. Verified in e2e (rows non-empty, same real data) | ✅ |
| B3 | Pass map with direction arrows, outcome filter, progressive highlight | `PassMap.tsx` — arrowheads for directionality, completed/incomplete filter, progressive passes highlighted distinctly (dashed style for incomplete, `strokeDasharray`) | ✅ |
| B4 | Honest "why don't I see this for every player" messaging | `EventMaps.tsx:114` — "Event-level data for this player is not yet available. Statlas currently has match event data for [covered competitions]" + link to `/data-coverage`; never a grayed-out "coming soon" | ✅ |
| B4-context | StatsBomb attribution per Constitution | `EventMaps.tsx` `statsbomb-attribution` note: "Data by StatsBomb — open data (CC BY-NC-SA 4.0)" | ✅ |

**Part B tests:** `tests/test_event_queries.py` — coverage gating ×3, pass queries + progressive derivation, competition-label fallback, covered-only competition list (6 tests). E2e: `web/e2e/phase3.spec.ts` — maps + data-table on Haaland (covered), honest note + zero pitch on De Bruyne (uncovered control), axe green on pitch components.

---

## Part C — Shareable Permalinks and Embeddable Widgets

| Req | Requirement | Evidence | Status |
|---|---|---|---|
| C1 | Stable permalink reproducing exact chart state (players + metrics + mode) | `web/lib/share.ts` `encodeRadarQuery`/`decodeRadarQuery`/`encodeTrendQuery`/`decodeTrendQuery` — query-string-encoded state; decode clamps to safe defaults/limits. Tests: `web/lib/share.test.ts:22,32,49` | ✅ |
| C1-note | Radar + Trend sharing; no Plot/Rank tool exists (Phase 2 never built one) | Sharing implemented for `radar` and `trend` kinds only — the tools that exist. No silent sharing for a non-existent tool (flag noted in this log, not silently skipped) | ✅ |
| C2 | Dynamic OG image renders the ACTUAL chart with ACTUAL data | `web/app/compare/og-image/route.tsx` + `web/app/trend/og-image/route.tsx` — server-rendered SVG of the real chart (satori-based), data fetched per config; `web/lib/chartSvg.test.ts` proves player names, axis labels, real values, raw-scale and 0–100 percent modes, and the gap-break are baked in; `svgDataUrl` base64 for `<img>` embedding | ✅ |
| C2-brand | Statlas wordmark subtly in the generated image | `ogFooter()` includes the wordmark/attribution line in every generated card | ✅ |
| C3 | Responsive `<iframe>` embed with "Powered by Statlas" attribution | `web/app/(embed)/embed/radar/page.tsx` + `embed/trend/page.tsx` — iframe targets reproducing the exact config from the query; `buildEmbedCode` (`share.ts`) generates a lazy-loaded iframe snippet; e2e verifies fresh-URL render + "Powered by Statlas" attribution | ✅ |
| C3-a11y | Embed accessible inside iframe context | Same components (RadarChart/TrendChart) with axe-green state; embed pages reuse the chart components with full accessible structure | ✅ |
| C3-perf | Lazy-load, minimal payload for third-party pages | Embed snippet lazy-loads (`loading="lazy"`), embed pages are lightweight client pages with no app chrome; verified rendering outside the main app styling context in e2e | ✅ |
| C3-doc | Copy-embed-code UI with real, tested snippet | `SharePanel.tsx` "Embed" button expands the generated iframe snippet with a copy action; snippet correctness unit-tested (`share.test.ts:75,85`) | ✅ |
| C4 | Consistent sharing panel with loading/success/error feedback | `SharePanel.tsx` — "Copy link" announces "Link copied" via `role="status"`, clipboard failure degrades to a selectable input with an error message (never silent) | ✅ |

**Part C tests:** `web/lib/share.test.ts` (7 tests) + `web/lib/chartSvg.test.ts` (5 tests). E2e: radar embed and trend embed render real charts from fresh URLs with no prior client state (Part D gate 6).

---

## Part D — Quality Gates

| Gate | Requirement | Evidence | Status |
|---|---|---|---|
| 1 | Gap-break test — deliberately constructed missing snapshot | `tests/test_trend.py:65 test_gap_is_flagged_not_interpolated` (asserts `gap_after` + `gap_ranges` — never a false line); `web/lib/chartSvg.test.ts:61` proves the OG SVG draws a dashed break | ✅ |
| 2 | Maps never render without `data_coverage` confirmation — automated test | `tests/test_event_queries.py:91,109,142` (no row / active / failed); e2e control case: uncovered player shows note and zero `.pitch` elements | ✅ |
| 3 | Permalink opened fresh reproduces the exact configuration | `web/lib/share.test.ts:22,32` round-trip tests; e2e opens `/embed/radar?...` and `/embed/trend?...` with no prior client state and asserts the real chart renders | ✅ |
| 4 | OG image contains real data values matching the config, not a placeholder | `web/lib/chartSvg.test.ts:18,42,61,84` assert real player names, values, modes in the generated SVG | ✅ |
| 5 | Accessibility audit on pitch components + data-table fallback | `web/e2e/phase3.spec.ts:73` — axe-core (`@axe-core/playwright`) green on the covered player's page with the data-table toggle open; runs in CI e2e job (violations fail the build) | ✅ |
| 6 | Manual embed test outside the app's styling context | Automated in CI e2e: embed pages render from a fresh URL with no app chrome; `buildEmbedCode` snippet validated in unit tests. Manual cross-site check remains listed as an optional human spot-check in `docs/suite/Testing.md` | ✅ |

---

## Verification summary

- **Automated test counts (post-Phase 3):** 104 pytest · 12 node unit tests · 15 e2e (5 specs × 375/768/1440 breakpoint projects).
- **CI run `31806249020` (commit `64651b7`):** all 5 jobs success — pytest+ruff (104 passed, ruff clean), typecheck + production build, e2e (15 passed, including all 6 `phase3.spec.ts` tests), Lighthouse (LCP < 2.5s), gitleaks.
- **Constitution compliance:** no fabricated data, coverage matrix is the arbiter of map rendering, recency/granularity labeled, StatsBomb attribution present, gap-honesty in trends, never colour-alone, full state sets (loading/empty/partial/error/limit) on every Phase 3 component.
- **Noted, not silently skipped:** Plot/Rank tool was never built in Phase 2, so sharing covers only the tools that exist (radar, trend) — no placeholder sharing UI for a non-existent tool.

## Files verified (primary evidence)

- `app/queries/trend_queries.py` — Part A query layer
- `app/queries/event_queries.py` + `app/api/main.py` (`/api/v1/players/{id}/trend|events|matches|shots|passes`, `/api/v1/coverage`) — Part B query/API layer
- `web/components/` — `TrendChart`, `TrendTool`, `TrendCard`, `EventMaps`, `ShotMap`, `PassMap`, `Pitch`, `SharePanel`, `EmbedRadar`, `EmbedTrend`
- `web/lib/` — `share.ts` (permalink/embed), `chartSvg.ts` (OG SVG), `ogRender.tsx` (OG card)
- `web/app/` — `compare/og-image/route.tsx`, `trend/og-image/route.tsx`, `(embed)/embed/{radar,trend}/page.tsx`, `trend/page.tsx`
- `tests/` — `test_trend.py`, `test_event_queries.py`
- `web/lib/` — `share.test.ts`, `chartSvg.test.ts`
- `web/e2e/` — `phase3.spec.ts` (new), `core.spec.ts`, `breakpoints.spec.ts`
