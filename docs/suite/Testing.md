# Testing.md — Statlas Testing Strategy

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-14 |
| Owner | QA + Staff Engineer |
| Status | In Review |

## 1. Test Pyramid

```mermaid
graph TD
    E2E[E2E — Playwright<br/>9 tests: radar gen, search/filter,<br/>axe, breakpoints, SSR smoke]
    INT[Integration — pytest<br/>pipeline end-to-end, idempotency,<br/>query-layer contracts]
    UNIT[Unit — pytest 104 + node 12<br/>scraper parsers (fixtures), math,<br/>lib functions (share/chartSvg/format)]
    E2E --> INT --> UNIT
```

**Rule:** the pyramid is enforced by CI counts — test *counts* are compared, not just pass/fail (Rules §4). A PR that deletes tests without replacement fails review.

## 2. Strategy per Layer

| Layer | Tool | Key suites |
|---|---|---|
| Python unit | pytest | scraper parsers vs saved fixtures (no live network); percentile/index math vs hand-computed cases; reconciliation edge cases (accents, "Jr.", nicknames) |
| Python integration | pytest + httpx TestClient | full weekly-refresh on fixture dataset → expected DB state; idempotency (run twice, no dupes); registry/matrix validation (test_matrix_validation.py) |
| TS/JS unit | node --test | `lib/share.test.ts`, `lib/chartSvg.test.ts` (12 tests) |
| Component/e2e | Playwright | `e2e/core.spec.ts` (radar generation, leaderboard filter, SSR profile, axe), `e2e/breakpoints.spec.ts` |
| Perf | @lhci/cli | Lighthouse CI — LCP < 2.5s enforced (failing threshold) |
| A11y | @axe-core/playwright | axe on /compare, player profile, team profile, leaderboard — fail on any violation |
| Security | gitleaks + pip-audit + npm audit | CI-enforced (SecurityAndCompliance §3) |

## 3. Critical Test Cases

| Area | Case | Expectation | CI |
|---|---|---|---|
| Radar generation (e2e) | search player → add to compare → chart renders | 4-player overlay renders with legend; pct↔per-90 toggle updates values | ✅ web job |
| Search/filter (e2e) | leaderboard filter by position/minutes | correct rows; sort indicator updates; pagination works | ✅ web job |
| SSR profile (e2e) | GET /players/[slug] | heading + data sentence + radar present; axe 0 violations | ✅ web job |
| Percentile math (unit) | known synthetic cohort | percentiles match hand-computed values exactly (formula = methodology.md) | ✅ python |
| Index math (unit) | weighted composite | index_score matches hand-computed weighted sum; NULL below 900 min | ✅ python |
| Idempotency (integration) | run pipeline twice | no duplicate snapshot rows (scrape_date+source key) | ✅ python |
| Anomaly gate (integration) | out-of-bounds value | flagged in ingestion_anomalies; snapshot not published until resolved | ✅ python |
| Tier completeness (regression) | cross-tier transfer same season | percentile unique key holds (tier dimension) — closeout C1 | ✅ python |
| Breakpoints (e2e) | 375/768/1440 × light/dark | zero horizontal overflow on core pages | ✅ web |
| Registry/matrix (unit) | §3 CI check | metric ids unique; weights sum 1.0; coverage matrix schema valid | ✅ python |

## 4. Breakpoint & Theme Matrix

Automated in `e2e/breakpoints.spec.ts`: for each page in {/, /compare, /players/[slug], /clubs/..., /leagues/..., /methodology} × viewport {375, 768, 1440} × theme {light, dark}: assert `document.scrollingElement.scrollWidth <= innerWidth`. Regression found + fixed during closeout: `.visually-hidden` tables (off-screen positioning), `.stat-item__label` wrapping, methodology table scroll wrappers.

## 5. Test Data Strategy

- **Fixture data** (`tests/fixtures/`): labeled, representative — mirrors real source HTML/JSON shapes (README-testing.md documents what each represents). Scrapers test against these, never live network.
- **Seed data** (`scripts/seed_dev_db.py`): deterministic fixture-demo DB through the *real* pipeline (28s); e2e boots this stack (production build).
- **Live validation** (non-CI): real Understat/StatsBomb syncs recorded in `docs/analytics/production-validation-log.md` — caught 3 real bugs fixture tests couldn't (backoff infinite loop, Understat API drift, StatsBomb JSON format change).

## 6. CI Gates

| Job | Gates |
|---|---|
| python | `ruff check .` + `pytest -q` (104) + `pip-audit` |
| security | gitleaks |
| web | `tsc --noEmit` + `npm audit --audit-level=high` + `npm run build` + Playwright (e2e + breakpoints + axe) |
| lighthouse | `lhci autorun` — LCP < 2.5s + category scores, failing threshold |
| (all) | require green before merge (Rules §3) |

## 7. Future: Checkout Flow Testing (Phase 4 stub)

When Stripe lands (TASK-4.1), add `e2e/checkout.spec.ts` (stub documented here so the plan exists): mock Stripe → select plan → redirect to Stripe → webhook → subscription state visible → gated feature unlocks. Uses Stripe's test mode keys in CI secrets (never committed).

## 8. Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Acceptance criteria per US/REQ verified here |
| [TechSpec.md](TechSpec.md) | NFR verification methods |
| [AppFlow.md](AppFlow.md) | State coverage asserted |
| [Design.md](Design.md) | Axe/contrast verification |
| [Schema.md](Schema.md) | Fixture data mirrors rows |
| [ImplementationPlan.md](ImplementationPlan.md) | DoD checklist references these gates |
| [Tracker.md](Tracker.md) | Gate status |
| [Rules.md](Rules.md) | §4 testing requirements |
| [API.md](API.md) | Contract tests (test_api.py) |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | Security gates |
| [Deployment.md](Deployment.md) | Test env provisioning |
| [Glossary.md](Glossary.md) | Terms |
| [RiskRegister.md](RiskRegister.md) | Risks that motivate gates |
