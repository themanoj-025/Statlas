# Performance baseline

*Status: enforced in CI (`.github/workflows/ci.yml` → `lighthouse` job)*

The Constitution's core performance target is **LCP < 2.5s on server-rendered
profile pages**. This document records the measured baseline, the enforcement
mechanism, and what the numbers mean.

## How it is measured

- Tool: **Lighthouse CI** (`@lhci/cli`, `web/lighthouserc.json`) — the same
  Chrome-based pipeline used for axe audits, run against a **production build**
  (`next start`, not dev mode).
- Stack under test: `web/scripts/e2e-server.sh` seeds the fixture-demo database
  through the real pipeline (seed → FastAPI → Next), then LHCI runs **3 passes**
  per page against:
  - `/players/erling-haaland` (player profile — the Constitution's LCP target page)
  - `/clubs/premier-league/manchester-city` (team profile)
- Preset: desktop, simulated throttling. Assertions are **error-level** — the CI
  job fails on violation, it does not just log.

## Baseline (measured 2026-08-14, fixture-demo dataset, production build)

| Page | LCP | Performance | Accessibility | SEO | Best practices | CLS |
| --- | --- | --- | --- | --- | --- | --- |
| Player profile (`/players/erling-haaland`) | 704–720 ms | 1.00 | 1.00 | 1.00 | 0.96 | ~0 |
| Team profile (`/clubs/premier-league/manchester-city`) | 572–579 ms | 1.00 | 1.00 | 1.00 | 0.96 | ~0 |

LCP is ~4× under the 2.5 s target. The pages are fully server-rendered with no
render-blocking third-party scripts and no unoptimized images (player/team
photos are placeholder blocks, not remote images).

## What the < 1.0 sub-scores are

The **best-practices 0.96** and the sub-100% audits under it are environment
artifacts of running `next start` directly without a CDN/reverse proxy, not
page defects:

- `uses-text-compression` (0.5): `next start` serves uncompressed; gzip/br is
  the reverse proxy's job (see `docs/engineering/infra-plan.md` — CDN layer).
- `legacy-javascript` / `unused-javascript`: Next.js ships per-route chunks;
  some polyfill/legacy code is unused on modern Chrome. Follows Next defaults.
- `errors-in-console` / `bf-cache`: dev-environment noise from the fixture
  dataset banner and SSR lifecycle; re-measured against real production data in
  the production-validation run before launch.
- `dom-size-insight`: leaderboard tables are paginated; profile pages are small.

None of these affect the Constitution's LCP gate. If a future run fails, fix
the cause — never lower the threshold.

## Enforcement

- **CI job `lighthouse`** in `.github/workflows/ci.yml` runs on every push/PR,
  boots the real stack, and fails unless every assertion in
  `web/lighthouserc.json` passes:
  - `largest-contentful-paint` ≤ 2500 ms (error)
  - `cumulative-layout-shift` ≤ 0.1 (error)
  - performance ≥ 0.85, accessibility = 1.0, SEO ≥ 0.9, best-practices ≥ 0.9
- Reports are uploaded as a build artifact (`lhci-reports/`) on every run,
  passing or failing, so the baseline stays inspectable.
- Local run: `cd web && npm run perf:audit` (requires the stack booted, or run
  the same boot sequence the CI job uses).

## When to re-measure

- After the **real production scrape** replaces fixture data (A5 in the closeout)
  — payload sizes may change; the gate must hold on real data before launch.
- After any change to page headers, fonts, or server-rendered data loading.
