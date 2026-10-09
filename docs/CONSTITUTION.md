# STATLAS — MASTER PROJECT CONSTITUTION

*The persistent context document to paste at the top of every phase-execution prompt.*

*Instructions for use: This is a reference document, not a one-time prompt. Paste it in full as the opening context block before every phase-specific prompt you give to an AI coding assistant. It establishes who Statlas is, how it must look, how it must be built, and what is explicitly forbidden — so every phase produces work consistent with every other phase.*

---

## 1. IDENTITY — WHO STATLAS IS

**Name:** Statlas (Stats + Atlas — "a comprehensive map of player data")

**One-line description:** Statlas is a football (soccer) data visualization and scouting analytics platform for scouts, analysts, agents, media, and serious fans — built on real per-90 and event-level statistics, with a transparent, published methodology.

**Positioning statement:** Statlas is the analytics platform that shows its work. Where competitors hide their formulas behind black boxes, every metric on Statlas traces back to a documented, public methodology. Statlas is precise, technical, and unglamorous by design — it is a tool for people who already understand the sport deeply, not a flashy consumer app.

**Voice and tone rules:**
- Technical and specific, never vague marketing language. Banned phrases: "unlock insights," "powerful analytics," "next-level," "game-changing," "revolutionize," "supercharge," "elevate your game" — any phrase that could apply to literally any SaaS product is forbidden.
- Every claim on the site must be backed by a real, checkable number or a linked methodology explanation. Do not write copy that asserts capability without evidence.
- Write like a football analyst talking to another football analyst, not like a startup pitching a general consumer.
- Humor is dry and rare, never forced. No exclamation points in body copy.

**Target users (in priority order):**
1. Independent scouts and analysts (freemium → convert to Pro)
2. Football media/content creators (drive embeds/backlinks)
3. Player agents (potential B2B/API tier)
4. Serious fans and fantasy football players (volume, free tier)
5. Smaller clubs without enterprise data budgets (future B2B tier)

**Naming and routes (anti-cloning rule):** Never copy DataMB's exact URL structure, tool names, or route naming 1:1. Statlas defines its own naming conventions and URL scheme once, in the design-system phase, and every phase reuses them. No route or tool name is chosen ad hoc.

---

## 2. VISUAL IDENTITY — DESIGN SYSTEM (NON-NEGOTIABLE)

**Rule zero: do not use default framework styling unmodified.** If you are using Tailwind, shadcn/ui, or any component library, override the default color palette, border-radius, and shadow tokens before building a single screen. A site that looks like an unmodified shadcn template is an immediate credibility failure for this project.

**Color system:**
- The primary palette must be defined as CSS custom properties / design tokens, not inline hex values scattered through components.
- Avoid the default "AI SaaS app" palette (indigo-600 / violet-500 gradients, purple-to-pink hero gradients). Choose a palette grounded in the actual product: pitch green, chalk white, a single confident accent color (a deep amber or a specific blue distinct from generic Tailwind `blue-600`), and a neutral gray scale with at least 8 steps for real hierarchy.
- Define semantic tokens: `--color-success`, `--color-warning`, `--color-danger`, `--color-data-positive`, `--color-data-negative` (percentile/stat coloring) — reference tokens everywhere, never hardcoded green/red per chart.
- **Dark mode is in scope from day one.** Both light and dark palettes are defined as tokens in the first design phase, and every component and chart is designed and tested in both. Dark mode is not a retrofit.
- **Colorblind safety is a requirement, not a nicety.** Define a tested categorical palette for comparison charts (teams, leagues, positions) that survives deuteranopia/protanopia simulation. Percentile scales use a defined diverging scale token. Numeric labels always accompany color encoding (see Accessibility).

**Typography:**
- Choose a real type scale (e.g., a modular scale of 1.25) with named steps (`--text-xs` through `--text-4xl`), not arbitrary pixel values per component.
- Exactly two typeface families, total, defined deliberately:
  1. One UI/display/body family (a distinctive face, not the default Inter/system-ui look every AI-generated site uses), used for headings, body copy, and UI text across its weight range.
  2. One data/table family for numeric content, with tabular figures (`font-variant-numeric: tabular-nums`) so columns of stats align.
- Never use Comic Sans. Never add a third family.
- Every numeric display — tables, badges, axis labels, percentiles — uses the data family with tabular figures.

**Spacing and layout:**
- Enforce an 8px base grid. All padding/margin/gap values are multiples of 8px; the 4px step is reserved exclusively for dense data tables and chart internals. No arbitrary "looks fine" spacing.
- Define a real breakpoint system (mobile 375px, tablet 768px, desktop 1440px minimum) and test every screen at all three — not just desktop.
- Leaderboards and long tables on mobile: sticky first column (player identity) plus horizontal scroll; never squeeze 10 columns into 375px.

**Components — every component must define ALL of these states explicitly, not just the "happy path":**
- Default / Loading / Empty / Error / Disabled / Hover / Focus (keyboard-visible focus rings defined as tokens, never removed).
- Charts specifically: the loading skeleton must match the actual chart shape (a radar skeleton looks like a radar outline, not a generic gray box). Empty state must explain WHY it's empty ("No players meet the 1,000-minute threshold in this league yet this season" — not just "No data").
- Motion is defined by tokens (duration + easing), not vibes: restrained by default, functional only (state transitions, hover feedback, no decorative flourish). Consistent with "unglamorous by design."

**Chart design language (applies to every visualization):**
- Value axes always start at zero unless the chart type demands otherwise (and then it is labeled).
- One consistent axis/gridline treatment across the whole site; no per-chart improvisation.
- No 3D charts, no gradients-on-charts, no default rainbow palettes — all chart colors come from the semantic/categorical tokens.
- Skeleton, empty, and error states follow the component rules above for every chart type.

**Iconography and imagery:**
- No stock photography. No generic illustration packs (no "flat design person pointing at floating chart" images).
- Real chart screenshots and real data visualizations ARE the hero imagery.
- One consistent icon library (e.g., Lucide) at one stroke width — never mix icon styles.

**Print and export (scout reports):** Every player-report view ships with a print stylesheet producing a clean PDF: readable type, token-based colors that survive grayscale, tabular numbers intact, recency line and source attribution printed on the report. Not a retrofit.

**Accessibility (mandatory, not optional):**
- WCAG AA contrast minimum on all text, in both light and dark themes.
- Every chart has an aria-label describing the actual data trend, not just "chart."
- All interactive elements keyboard-navigable.
- Never convey information by color alone — percentile colors must also have a numeric label.
- An automated axe audit runs in CI on every PR and must be green to merge (see Engineering).

---

## 3. DATA PHILOSOPHY (NON-NEGOTIABLE)

**Rule zero: never fabricate a number, ever — not even temporarily, not even in a dev/demo environment.** Placeholder data is the single fastest way this project reads as fake. If real data isn't wired up yet for a screen, that screen shows an explicit "data pending" state — it does not show made-up statistics.

**Data sourcing (for MVP, must remain free-tier compatible):**
- FBref: primary source for per-90 stats (passing, defense, possession, shooting, GK). FBref actively blocks automated access and its terms restrict scraping/redistribution; treat it as a high-risk, best-effort source with mandatory throttling, exponential backoff, robots.txt compliance, and a documented fallback path. Migrating to a licensed feed is a planned event, not an emergency.
- Understat: xG/xA supplement, top 5 European leagues only, parsed from embedded JSON.
- StatsBomb Open Data (public GitHub repo): event-level data (x/y coordinates) for shot maps and pass maps — coverage limited to specific released competitions, must be explicitly labeled as such in the UI, never implied to be universal. **StatsBomb's terms require that any published analysis based on their data states the data source as StatsBomb and uses their logo — this attribution is mandatory on every page that renders StatsBomb-derived content, and it is enforced by review, not goodwill.**
- API-Football free tier: fixtures/live scores layer only.

**The Data Coverage Matrix (the enforcement mechanism for "no overclaiming"):**
- A machine-readable file in the repo (e.g., `data/coverage_matrix.json`) is the single source of truth for what data exists: source × league × season × stat categories × update cadence × required attribution.
- The `/data-coverage` page renders from it. UI components read from it. Tests assert against it: a screen cannot claim coverage the matrix doesn't contain — this rule is enforced mechanically, not by discipline.
- Any phase that adds or removes data updates the matrix in the same commit.

**Data pipeline requirements:**
- Every ingestion job is a tested, idempotent module — re-running it does not duplicate or corrupt data.
- Player name reconciliation across sources (FBref vs. Understat spell names differently) is an explicit mapping step with logged mismatches for manual review, never a silent best-guess join. Where sources conflict on the same stat, a documented precedence rule decides the winner — precedence is decided per metric in the Metric Registry (see §5), never ad hoc at runtime.
- Every stat snapshot is versioned by scrape date — historical data is append-only and never overwritten or mutated in place.
- An anomaly-detection pass runs on every data refresh: values outside plausible bounds are flagged and blocked from publication until reviewed. Flagged values are never silently published.
- The qualification threshold for inclusion (minimum minutes played) is documented, justified, and displayed to users — never hidden. A player below threshold shows an explicit "pending qualification" state, not a stat.
- **Recency labeling is mandatory:** every stat block and every page carries "Data as of YYYY-MM-DD" (snapshot) and, where applicable, "computed on YYYY-MM-DD" (derived values). Batch-updated data is never presented as live. The word "live" is used only for the API-Football fixtures layer.
- **Null vs. zero policy:** every metric defines in its registry entry whether a missing value displays as N/A or 0 — the ambiguity is resolved per metric and never left to the rendering layer.
- **Sample context:** no stat is displayed without its sample context (minutes played, matches, qualification status) available at one click.

**Methodology transparency:**
- Every derived/proprietary metric (the "Statlas Index" or equivalent) must have a published, plain-language methodology page explaining exactly how it's calculated, with the actual formula shown — this is the primary trust and differentiation lever versus black-box competitors.
- Methodology pages are generated from the Metric Registry (§5) so they cannot drift from the code that produces the numbers.

**Privacy and legal compliance (non-negotiable):**
- Player performance statistics are personal data under GDPR. There is no "public figure" exemption, and a commercial analytics tool generally cannot claim the journalistic exemption. Statlas therefore: (a) documents a legitimate-interests assessment (Art. 6(1)(f)) covering its processing purposes before launch; (b) defines a retention policy — historical snapshots are retained as statistical/archival records under a documented policy, not indefinitely "just in case"; (c) implements a data-subject request path (access, rectification, erasure) that is actually operational, not a dead mailbox; (d) records all of this in the Privacy Policy in language that matches what the site actually does (see §5).
- Source terms are reviewed before any source is wired up, and the review outcome is recorded in the coverage matrix. Attribution obligations (e.g., StatsBomb logo + source statement) are treated as UI requirements, not legal footnotes.

---

## 4. ENGINEERING STANDARDS (NON-NEGOTIABLE)

**Architecture:**
- Frontend: Next.js (React) — server-rendered player/team pages for real SEO indexability, not client-only rendering.
- Backend: FastAPI (Python) or Node.js API layer, PostgreSQL for structured data, Redis for caching computed percentile/leaderboard queries.
- The data-source layer is modular/swappable — scraper functions behind an interface, so migrating to a licensed feed (Wyscout/Opta/Sportmonks) later does not require rearchitecting the application.
- The API is versioned from day one (even if v1 is internal), because a B2B/API tier is a stated future target.

**Code quality:**
- Every data-parsing function has a unit test — scraped HTML structures change; failures must be loud (logged, alerted) not silent.
- Every API endpoint has input validation and explicit error responses, not generic 500s.
- No hardcoded secrets/API keys in source — environment variables only, with a documented `.env.example` and a secret-scanning check in CI.
- Meaningful git commit messages that describe what and why, not "update," "fix," "wip" — commit history reads as a real development log.

**CI/CD (the enforcement mechanism for "tested before shipped"):**
- Every PR runs: unit tests, typecheck, lint, and the axe accessibility audit. A red check blocks merge. No direct pushes to main.
- Deploys are gated on green CI and use a staging environment that mirrors production (same stack, same env-var shape) — no prod-only bugs.
- The coverage matrix and Metric Registry are validated by a CI check (schema validity, uniqueness of metric IDs, no UI claims beyond the matrix).

**Observability and operations:**
- Structured logging throughout; scraper and pipeline failures page an alert, they do not just log and continue.
- PostgreSQL backups run on a schedule and the restore procedure is tested — a broken backup is a failed backup.
- Data-pipeline runs are monitored for success rate and volume drift (a scrape that silently returns half the expected rows is a failure, not a smaller update).

**Security:**
- SSRF guard on any code that fetches URLs (the scraper layer never follows user-controlled URLs).
- Rate limiting on public API endpoints from day one.
- Dependency scanning (known-vulnerability check) in CI.
- Auth for Pro/B2B tiers is designed with a real strategy (e.g., subscription-managed access, API keys with rotation) — not bolted on.

**Performance:**
- Server-rendered pages must hit real Core Web Vitals targets (LCP < 2.5s) measured in CI, not "seems fast on my machine."
- Chart rendering must not block the main thread on large datasets — virtualize/paginate leaderboard tables rather than rendering thousands of rows at once.

**Testing minimum bar before any phase is considered "done":**
- Data pipeline: unit tests on parsers + integration test on end-to-end scrape-to-database flow.
- Critical UI paths (radar generation, search/filter, subscription checkout): at least basic end-to-end test coverage.
- Accessibility: automated axe audit green in CI — issues resolved, not noted.

---

## 5. CONTENT AND COPY RULES

**The Metric Registry (methodology-as-code):**
- Every metric — including every derived/proprietary one — has a registry entry: stable id, name, plain-language definition, exact formula, units, source(s) with precedence, minutes floor, display rules (null-vs-zero), percentile color token, and methodology-page slug.
- The Methodology page is generated from the registry. A change to any metric's formula ships with its registry entry and methodology text updated in the same commit — a formula change without its methodology update is a failed change.
- A metric without a registry entry does not exist; it cannot be referenced by UI or copy.

**Data-driven sentences:**
- Every player/team page must include at least one unique, data-driven sentence generated from that player's actual numbers (e.g., "ranks in the 87th percentile for progressive passes among Premier League midfielders this season") — never a templated sentence with no real substitution, and never a fabricated stat.
- These sentences are produced by a DB-backed sentence generator (templated functions that call the real database), with unit tests covering grammar, pluralization, ranges, and boundary cases (percentile 0, tiny samples, league with zero qualifying players). This is the implementation of Never-List rule #4: no free-generated numeric claims, ever.

**Coverage and attribution copy:**
- Any page rendering StatsBomb-derived content carries the required source attribution and logo, plus a recency line.
- Data coverage statements on the site (league tables, competition filters, shot-map availability) are generated from the coverage matrix — copy cannot claim more than the matrix contains.

**Standing content:**
- The Methodology/Guide page is written in full before launch, not stubbed — it is the credibility anchor of the entire product.
- A dated, honest changelog is started during development (not backfilled at launch) and maintained going forward.
- Legal pages (Terms of Service, Privacy Policy) are drafted specifically for this product's actual data practices — including the GDPR position and retention policy from §3 — not a generic copy-pasted template.

---

## 6. THE "NEVER DO THIS" LIST (hard constraints for every phase)

1. Never ship placeholder/lorem-ipsum content or fabricated statistics to any environment users can see, including demos.
2. Never use an unmodified default component-library theme.
3. Never copy DataMB's exact URL structure, tool names, or route naming 1:1.
4. Never let the AI assistant free-generate a numeric claim — it must call a real function against the real database.
5. Never silently swallow a data pipeline error — log it, surface it, never guess and publish.
6. Never ship a chart without loading, empty, and error states designed.
7. Never hardcode credentials or skip environment-variable configuration.
8. Never claim data coverage the product doesn't actually have (e.g., implying shot maps exist for all leagues when StatsBomb Open Data only covers specific competitions). The coverage matrix is the arbiter of what can be claimed.
9. Never use vague marketing copy in place of specific, checkable claims.
10. Never skip the accessibility pass "for now" — it does not get retrofitted later in practice.
11. Never mutate, overwrite, or "fix" a historical snapshot — data is append-only and versioned by scrape date.
12. Never display a stat without its recency label, and never present batch-updated data as live.
13. Never display an ambiguous null-vs-zero value — the per-metric policy from the registry governs.
14. Never ship a metric formula change without its registry entry and methodology page updated in the same commit.
15. Never run scrapers without throttling, backoff, and robots.txt compliance; never let a scraper failure pass unalerted.
16. Never ship a new metric without a registry entry, unit tests on its parser/formula, and its methodology text.

---

## 7. DEFINITION OF DONE — PER PHASE

Before any phase is declared done, all of the following must hold (the checklist operationalizes this constitution):

- [x] Data pipeline work: parser unit tests + scrape-to-database integration test pass. _(Closed by closeout 2026-08-14: 104 pytest tests green incl. scraper unit tests against fixtures, full-pipeline integration test, idempotency proof; live Understat + StatsBomb validation run.)_
- [x] Critical UI paths touched: e2e tests added/passing for radar generation, search/filter, checkout. _(Radar generation + search/filter passing in Playwright e2e in CI — closeout B3. Checkout: re-scoped to Phase 4 — billing does not exist yet; a documented stub lives in `web/e2e/core.spec.ts` and Phase 4 must add checkout coverage before Pro goes live.)_
- [x] axe accessibility audit green in CI; issues resolved. _(Automated via @axe-core/playwright on radar/player/team/leaderboard pages, fails the build on any violation — closeout B2. One real contrast violation found and fixed (dataset banner amber-on-muted 4.47:1 → 6.3:1).)_
- [x] Coverage matrix updated if sources/leagues/stats changed; CI matrix validation passes. _(`tests/test_matrix_validation.py` — registry schema/uniqueness/weights-sum-to-1, tier completeness, coverage rows well-formed, no UI claim beyond the matrix; enforced in CI via pytest — closeout B5.)_
- [x] Metric Registry updated for every new/changed metric; Methodology page generated and consistent. _(Registry is the methodology-as-code source; the /methodology page renders from it; `tests/test_matrix_validation.py` asserts consistency — closeout B5.)_
- [x] Recency labels and required source attribution present on all affected pages. _(Player/team pages label the qualifying season/snapshot date; dataset-mode banner is site-wide; coverage page lists attribution per source.)_
- [x] Changelog entry added, dated, honest. _(2026-08-14 closeout entry: live-pipeline fixes, tier gate, timezone policy, Postgres parity, security CI, automated quality gates — see `/changelog`.)_
- [x] `.env.example` and any new env vars documented; no secrets in source. _(`.env.example` tracked; gitleaks secret scan enforced in CI — closeout C5.)_
- [x] Performance budget (LCP < 2.5s) verified for affected server-rendered pages. _(Lighthouse CI enforces LCP ≤ 2500ms + CLS ≤ 0.1 on player/team profiles on every PR; measured 572–720ms — closeout B1, `docs/engineering/performance-baseline.md`.)_
- [x] Every component added has its full state set (default/loading/empty/error/disabled/hover/focus), tested at 375/768/1440px, in both themes. _(Automated no-horizontal-overflow matrix at 375/768/1440px in light + dark — closeout B4; state set specified per component in `docs/suite/Design.md`.)_

---

## 8. HOW TO USE THIS DOCUMENT

For every phase-execution prompt (Phase 0 through Phase 5 of the build plan), open the prompt with:

> "Here is the Statlas Master Project Constitution. Everything you build in this phase must comply with every rule in it. [paste this full document]. Now, here is the Phase [N] task: ..."

This ensures design consistency, data integrity rules, and engineering standards persist across every separately-executed phase, even though each phase is a distinct prompt/session.

---

## Revision history

| Rev | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-10 | **Initial constitution.** |
| 1.1 | 2026-08-10 | **Strengthened.** Added: Data Coverage Matrix (§3); Metric Registry with methodology-as-code (§5); recency labeling + null-vs-zero policy (§3); GDPR/legal compliance subsection incl. source-terms review (§3); CI/CD gates, observability, backups, security, API versioning (§4); dark mode + colorblind-safe palettes + motion tokens + chart design language + print/export (§2); typeface rule tightened to exactly two families and grid rule tightened to 8px/4px-reserved (§2); Definition of Done checklist (§7); Never-List items #11–#16 (§6). |
