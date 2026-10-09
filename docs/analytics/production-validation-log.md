# Production validation log

*Created: 2026-08-14 (Phase 0–2 closeout, Part A).*

This is the evidence trail for the real-data validation work done in the
closeout. The pipeline's Phase 1 output requirement was: "a real scrape must be
run and validated before this pipeline is considered production-ready." This log
records exactly what was run against live sources, what was found, what was
fixed, and what still blocks the production flip. It is written to be checkable —
every claim below maps to a concrete run or a specific commit.

## Dataset-mode decision

**`STATLAS_DATASET_MODE` remains `fixture-demo` at the close of this work.**

The flip to `production` is **blocked**, not skipped, by two external items:

1. **FBref** returns HTTP 403 to the standard pipeline (bot-blocked) from this
   build environment — even with the project's descriptive User-Agent and
   10s+2s jitter rate limit. A real FBref scrape is the primary source for the
   per-90 stat tables and **cannot be validated here**. A credentialed or
   proxied run is required (tracked: `docs/legal/pre-launch-human-actions.md`
   item 4.2).
2. **API-Football** requires a paid/free-tier API key that does not exist in
   this environment (tracked: item 4.1).

Flipping the mode without a validated FBref run would make the product claim
production data it does not have — exactly what the Constitution's coverage
rules exist to prevent. The mode flip therefore ships in the same change as the
validated FBref + API-Football runs.

Meanwhile, the pipeline's real-data paths were exercised against the two
sources that ARE reachable (Understat, StatsBomb Open Data), and that work found
and fixed real bugs — documented below.

## A2 — Understat live validation (PASSED, with fixes)

**What was run:** the live `https://understat.com/league/EPL/2025` page was
fetched with the project's User-Agent and parsed by the real scraper path.

**Result:** 562 real player records extracted with all registry metrics.

**Drift found (real-world — exactly what fixture tests can't catch):**
Understat changed its page structure. The embedded `playersDataObject` JSON —
which the scraper parsed — is **gone from the static HTML**; player data now
loads via JavaScript from a POST endpoint (`/main/getPlayersStats/`). The
fixture-based tests still passed because they test the old payload shape.

**Fixes (committed):**
- `app/sources/base.py`: `fetch_with_retry` now supports POST bodies; fixed a
  separate infinite-loop bug in `backoff_delays()` (once the delay hit the cap,
  `min(d * factor, cap)` never advanced → `MemoryError` on repeated failures).
- `app/sources/understat.py`: falls back to the POST endpoint when the embedded
  payload is absent, raising a loud, specific `UnderstatSchemaChangedError`
  only if both paths fail.
- `tests/test_understat.py`: fixture from the live response + tests for the
  fallback path. Suite: 104 pytest green.

**Rate limit honored:** the configured `UNDERSTAT_DELAY_SECONDS` (5s) governs
requests; the validation run issued a handful of requests total.

## A3 — StatsBomb Open Data real sync (PASSED, with fixes)

**What was run:** the real sync pulled `competitions.json` from the public
GitHub repo and ingested 2 matches of a live competition-season (bounded for
validation), writing 7,025 real match events plus `data_coverage` rows.

**Drift found:** `competitions.json` changed shape — it is now a **flat list of
competition-season entries**, not the nested `seasons` array the original
parser assumed.

**Fixes (committed):** `app/sources/statsbomb.py` `sync_competition` now handles
both the legacy nested format and the live flat format; tests updated.

**Coverage-table accuracy (the A3 gate):** verified the `data_coverage` rows
written by the real sync reflect exactly the competitions/seasons ingested —
the shot/pass-map coverage-gating logic reads this table, so an inaccurate
matrix would hide features it should show or falsely imply coverage. Verified
correct after the real run. Note recorded: the demo seed labels comp 12 as
"Premier League"; the live competitions file identifies it as **Serie A** — a
labeling nuance to reconcile in the production seed (does not affect coverage
gating, which keys on source identifiers, not labels).

## A1 — FBref live scrape (BLOCKED — see dataset-mode decision above)

**What was attempted:** live FBref league pages with the project's User-Agent
and compliant rate limit. **Result:** HTTP 403 (bot-blocking) on all attempts
from this environment. Not a scraper failure — the scraper's fixtures and
defensive parsing are tested (unit + integration), but a live run requires
network access FBref denies here. The anomaly-detection and reconciliation
passes will be run against real FBref data as part of the credentialed run
(they already run in the weekly-refresh pipeline and are covered by tests).

## A4 — Cross-source validation (DEFERRED to the FBref run)

FBref data is required for the 20-player cross-source comparison (shots,
xG-adjacent figures). Understat alone cannot satisfy it, so this gate is
explicitly deferred with the FBref block. No reconciliation/parsing bug was
revealed by the Understat real run — the POST-endpoint field names match the
embedded payload's.

## What was NOT faked

- No synthetic numbers were substituted for real data anywhere in this log.
- The Understat 562-record extraction and StatsBomb 7,025-event ingestion are
  real network results, reproducible with the committed scraper code.
- The dataset banner and `/data-coverage` page continue to say
  `fixture-demo` honestly; the mode will flip only with the validated FBref
  run (blocking items above).

## Re-validate before launch

- [ ] FBref credentialed/proxied scrape for ≥ 2 leagues (one top-5, one
      second-tier) + anomaly review + reconciliation review (A1)
- [ ] Cross-source comparison ≥ 20 players FBref vs Understat (A4)
- [ ] API-Football live run with real key (fixtures layer)
- [ ] Re-run LHCI + e2e against production data (performance gate must hold on
      real payloads — see `docs/engineering/performance-baseline.md`)
- [ ] Flip `STATLAS_DATASET_MODE=production`; update this log with results
