# Statlas — Project Overview

<p align="center">
  <em>Football analytics that shows its work.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-144E33" alt="Version 0.2.0" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" alt="React 19" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/github/license/themanoj-025/Statlas" alt="License: AGPL-3.0" />
</p>

> **How to use this document:** read top to bottom once, then jump to any section via the
> table of contents. Every file in the repository (180 tracked files) is documented in
> §6. Facts are labeled **explicit** (stated in code/comments) or **inferred** (deduced
> from naming/convention).

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Tech Stack & Core Technologies](#2-tech-stack--core-technologies)
- [3. High-Level Architecture](#3-high-level-architecture)
- [4. Complete Folder Structure Tree](#4-complete-folder-structure-tree)
- [5. If You Only Read 5 Files, Read These](#5-if-you-only-read-5-files-read-these)
- [6. Exhaustive File-by-File Breakdown](#6-exhaustive-file-by-file-breakdown)
  - [6.1 Root files](#61-root-files)
  - [6.2 `app/` — Python backend](#62-app--python-backend)
  - [6.3 `app/api/` — FastAPI layer](#63-appapi--fastapi-layer)
  - [6.4 `app/compute/` — computation jobs](#64-appcompute--computation-jobs)
  - [6.5 `app/config/` — locked configuration](#65-appconfig--locked-configuration)
  - [6.6 `app/orchestration/` — pipeline jobs](#66-apporchestration--pipeline-jobs)
  - [6.7 `app/queries/` — data-access layer](#67-appqueries--data-access-layer)
  - [6.8 `app/sources/` — data-source adapters](#68-appsources--data-source-adapters)
  - [6.9 `scripts/` — dev/ops scripts](#69-scripts--devops-scripts)
  - [6.10 `tests/` — test suite](#610-tests--test-suite)
  - [6.11 `web/` — Next.js frontend (lib, components, app, e2e)](#611-web--nextjs-frontend)
  - [6.12 `docs/` — documentation](#612-docs--documentation)
  - [6.13 `data/` and `.github/`](#613-data-and-github)
- [7. Data Models & Schemas](#7-data-models--schemas)
- [8. API Surface](#8-api-surface)
- [9. Configuration & Environment Variables](#9-configuration--environment-variables)
- [10. Build, Run & Deployment Instructions](#10-build-run--deployment-instructions)
- [11. Data & Control Flow Walkthroughs](#11-data--control-flow-walkthroughs)
- [12. Dependency Graph Summary](#12-dependency-graph-summary)
- [13. Testing Strategy](#13-testing-strategy)
- [14. Known Issues, Technical Debt & Assumptions](#14-known-issues-technical-debt--assumptions)
- [15. Security Notes](#15-security-notes)
- [16. Performance Considerations](#16-performance-considerations)
- [17. Glossary](#17-glossary)
- [18. Changelog / Version History Summary](#18-changelog--version-history-summary)
- [19. How to Extend This Project](#19-how-to-extend-this-project)
- [20. Suggested Onboarding Path](#20-suggested-onboarding-path)
- [21. Appendix — Files Not Elsewhere Classified](#21-appendix--files-not-elsewhere-classified)

---

## 1. Executive Summary

**Statlas** *(explicit — from README.md and the codebase)* is a football
data-visualization and scouting platform. It ingests per-90 player statistics from
FBref, Understat and API-Football, plus event-level data from StatsBomb Open Data,
normalizes it through a versioned snapshot pipeline, computes percentile ranks and a
proprietary composite metric (the **Statlas Index**), and surfaces the results through a
server-rendered Next.js site: radar comparisons, snapshot trend charts, shot/pass maps,
leaderboards, player/team/league profiles, and shareable embeddable widgets.

**Who it's for** *(explicit — README)*: scouts, analysts, agents, media, and serious fans.
The site map and navigation docs prioritize the scouting/analysis workflow (compare →
embed) above casual browsing.

**The problem it solves** *(inferred from the Constitution and product docs)*: football
statistics are scattered across sources with different definitions, update cadences, and
licensing terms, and most consumer tools present numbers without saying where they came
from or what they mean. Statlas's differentiator is **honesty by construction**: every
number carries a dated snapshot, every metric has a published definition (methodology-as-code),
coverage claims are gated by a machine-readable matrix, missing history is drawn as a gap
rather than interpolated, and nothing is ever presented as data that isn't.

**Why it exists** *(explicit — the Constitution)*: the project is built in governed phases
(0 = design/legal, 1 = pipeline, 2 = radar/profiles, 3 = trends/maps/embeds, 4 = billing,
5 = B2B) under a persistent "Master Constitution" that locks data-integrity rules,
design non-negotiables, and a never-do list. This document reflects the repository at the
close of Phases 0–3 plus a hardening closeout (August 2026).

**Current data status** *(explicit — `docs/analytics/production-validation-log.md`)*: the
pipeline serves a **labeled fixture-demo dataset** (`STATLAS_DATASET_MODE=fixture-demo`).
Real Understat and StatsBomb syncs were run and validated during the closeout; FBref is
bot-blocked (HTTP 403) from the build environment, so the flip to `production` is blocked
on a credentialed FBref run plus an API-Football key.

---

## 2. Tech Stack & Core Technologies

| Layer | Technology | Version | Purpose |
| --- | --- | --- | --- |
| Language (backend) | Python | 3.10+ (code floor), 3.14 (dev/CI) | All pipeline, compute, API code |
| Language (frontend) | TypeScript | 5.7 | All web code, strict mode |
| Web framework | Next.js | 16.3.0 | App Router, server-rendered pages, API routes for OG images |
| UI library | React | 19.2.8 | Client components |
| API framework | FastAPI | >= 0.110 | Versioned `/api/v1` REST layer |
| ASGI server | Uvicorn | >= 0.29 | Runs the FastAPI app |
| ORM | SQLAlchemy | 2.x | ORM models mirroring `schema.sql` |
| Database (prod) | PostgreSQL | 16 (compose image) | Canonical DDL in `app/schema.sql` |
| Database (dev/test) | SQLite | stdlib | In-memory for tests, file-based `data/dev.db` for dev |
| HTML parsing | BeautifulSoup 4 | >= 4.12 | FBref table parsing |
| HTTP | requests | >= 2.31 | All source fetching |
| Web fonts | Sora + IBM Plex Sans | via next/font | Two-family type rule (design system §4) |
| Icons | lucide-react | ^0.460.0 | UI icons |
| Testing (Python) | pytest | >= 8.0 | 104 tests |
| Linting (Python) | ruff | via pyproject | Enforced rule set: F, E4/E7/E9, I, DTZ |
| Testing (frontend) | node --test | Node 24 | 12 unit tests (pure modules) |
| E2E | Playwright | ^1.62.1 | 9 e2e tests incl. axe + breakpoints |
| A11y audit | @axe-core/playwright | ^4.13.0 | axe scans on 4 Phase-2 pages |
| Perf audit | @lhci/cli + lighthouse | ^0.15.1 / ^13.4.1 | LCP < 2.5s enforced in CI |
| Secret scan | gitleaks | action v2 | CI job |
| Dep scan (Python) | pip-audit | CI step | Enforced |
| Dep scan (npm) | npm audit | CI step | `--audit-level=high` enforced |
| Container | Docker / docker compose | v2 | Postgres + API + web + seed |
| CI/CD | GitHub Actions | workflow | 5 jobs: python, security, web, e2e, lighthouse |
| Data sources | FBref, Understat, StatsBomb Open Data, API-Football | — | External (see §6.8) |

---

## 3. High-Level Architecture

```
                    ┌─────────────────────────────────────────────────────┐
                    │                 DATA SOURCES (external)             │
                    │  FBref · Understat · StatsBomb Open Data · API-FB   │
                    └───────────────┬─────────────────────────────────────┘
                                    │ scrape/sync (throttled, cached, UA-identified)
                                    ▼
                    ┌─────────────────────────────────────────────────────┐
                    │  app/sources/*  (StatsSource interface)             │
                    │  → normalized RawPlayerStatRecord / FixtureRecord   │
                    └───────────────┬─────────────────────────────────────┘
                                    ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │  app/orchestration/weekly_refresh.py  (the pipeline job sequence)  │
        │  scrape → ingest → reconcile → anomaly-check → percentiles+index → │
        │  publish  (+ optional StatsBomb sync + event link + fixtures)      │
        └───────────────┬─────────────────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │  PostgreSQL (schema.sql) / SQLite (dev)                             │
        │  leagues · teams · players · aliases · stat_snapshots ·             │
        │  percentile_snapshots · match_events · data_coverage ·             │
        │  ingestion_anomalies · reconciliation_queue · fixtures             │
        └───────────────┬─────────────────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │  app/queries/*  — THE data-access layer (published-only reads)     │
        │  player · leaderboard · league · team · trend · event · coverage · │
        │  sentences · similar_players                                       │
        └───────────────┬─────────────────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │  app/api/*  — FastAPI /api/v1 (the ONLY thing the web talks to)    │
        │  main.py routes · player_view.py payload builders ·                │
        │  registry_view.py public metric metadata                           │
        └───────────────┬─────────────────────────────────────────────────────┘
                        ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │  web/  — Next.js 16 (server-rendered)                              │
        │  app/* pages (SSR) → lib/api.ts → FastAPI                          │
        │  components/* client charts · lib/share.ts permalinks ·            │
        │  lib/chartSvg.ts + ogRender.tsx (dynamic OG images)                │
        └─────────────────────────────────────────────────────────────────────┘
```

**Architectural pattern** *(inferred from folder evidence, documented in
`docs/suite/TechSpec.md`)*: a **layered architecture with a strict one-way data
flow** — `pipeline → DB → queries → API → web`. The evidence: `app/queries/` is described
in comments as "THE data-access layer" and `app/api/main.py` states "This is the ONLY
data-access layer the frontend talks to"; no web component imports SQLAlchemy. The design
is deliberately **not** microservices (one Python package, one web app) and **not** MVC
in the framework sense (Next.js App Router with server components; FastAPI has no
view-model layer separate from routes). Additional patterns:

- **Repository/query pattern**: `app/queries/*` are thin functions taking a `Session` —
  the API layer is a thin wrapper.
- **Strategy pattern**: `StatsSource` ABC with one concrete class per data provider —
  documented as the swappable data-source layer (Constitution §4).
- **Event-sourcing-lite**: `stat_snapshots` are append-only, versioned by `scrape_date`;
  percentile rows are never updated in place (immutability requirement).
- **Gateway/anti-corruption layer**: each scraper normalizes foreign payloads into
  `RawPlayerStatRecord` so downstream code never sees source-specific shapes.

---

## 4. Complete Folder Structure Tree

```
Statlas/
├── .dockerignore
├── .env.example
├── .gitattributes
├── .github/
│   ├── dependabot.yml
│   └── workflows/ci.yml
├── .gitignore
├── Dockerfile                     # API image (FastAPI + uvicorn, non-root)
├── LICENSE                        # AGPL-3.0
├── PROJECT_OVERVIEW.md            # this document
├── README.md
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py            (implied; not tracked separately)
│   │   ├── main.py                # FastAPI app, /api/v1 routes
│   │   ├── player_view.py         # player payload builders (SSR aggregate)
│   │   └── registry_view.py       # public metric metadata (methodology-as-code)
│   ├── cli.py                     # pipeline CLI (weekly-refresh, scrape, reconcile, anomalies)
│   ├── compute/
│   │   ├── __init__.py
│   │   ├── anomaly_check.py       # bounds + cross-source anomaly detection
│   │   ├── index.py               # Statlas Index pure calc + verifier
│   │   └── percentiles.py         # percentile + index computation job
│   ├── config.py                  # env settings, registry/tier loaders
│   ├── config/
│   │   ├── metric_registry.json   # 16 metrics, weights, bounds, floors (methodology-as-code)
│   │   ├── tiers.json             # league tiers + external ids
│   │   └── pricing.json           # plan boundaries + limits (incl. workspace caps)
│   ├── db.py                      # engine/session management
│   ├── models.py                  # ORM models mirroring schema.sql
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── event_link.py          # StatsBomb event → player name linking
│   │   └── weekly_refresh.py      # the weekly pipeline job
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── coverage_queries.py    # coverage matrix arbiter
│   │   ├── event_queries.py       # shot/pass event data, coverage-gated
│   │   ├── leaderboard_queries.py # published leaderboard rows
│   │   ├── league_queries.py      # league catalog, stats tables, teams
│   │   ├── player_queries.py      # profiles, percentiles, search, slug resolution
│   │   ├── sentences.py           # data-driven profile sentences
│   │   ├── similar_players.py     # cosine-similarity nearest neighbours
│   │   ├── team_queries.py        # team profiles, roster, squad radar
│   │   ├── trend_queries.py       # snapshot-history trends
│   │   └── workspace_queries.py   # shortlists/entries/notes/tags/history + authz (Phase 7)
│   ├── api/
│   │   ├── main.py                # FastAPI app — the ONLY data-access layer
│   │   ├── player_view.py         # player profile payload builder
│   │   ├── public_views.py        # public API keys/rate limits
│   │   ├── registry_view.py       # methodology meta
│   │   ├── billing_views.py       # auth + Stripe (Phase 4)
│   │   ├── assistant_views.py     # grounded AI assistant (Phase 4)
│   │   └── workspace_views.py     # workspace routes, session auth (Phase 7)
│   ├── reconciliation.py          # player name reconciliation
│   ├── schema.sql                 # canonical PostgreSQL DDL
│   └── sources/
│       ├── __init__.py
│       ├── api_football.py        # fixtures/live layer + daily budget
│       ├── base.py                # StatsSource ABC, rate limiter, cache, retry
│       ├── fbref.py               # FBref scraper (primary)
│       ├── statsbomb.py           # StatsBomb Open Data sync
│       └── understat.py           # Understat xG/xA (Big-5)
├── data/
│   └── coverage_matrix.json       # generated by seed; tracked (Constitution §3)
├── docker-compose.yml
├── docs/
│   ├── CONSTITUTION.md
│   ├── CONTRIBUTING.md
│   ├── README.md                  # master docs index
│   ├── analytics/
│   │   ├── data-compliance-notes.md
│   │   ├── methodology.md
│   │   ├── percentile-rules.md
│   │   └── production-validation-log.md
│   ├── engineering/
│   │   ├── cleanup-audit-2026-08-14.md
│   │   ├── infra-plan.md
│   │   ├── performance-baseline.md
│   │   ├── postgres-parity-notes.md
│   │   └── timezone-policy.md
│   ├── legal/
│   │   ├── founder-legal-checklist.md
│   │   ├── pre-launch-human-actions.md
│   │   ├── privacy-policy-draft.md
│   │   └── terms-of-service-draft.md
│   ├── product/
│   │   └── scouting-pipeline.md    # Phase 7 status pipeline rules + integrity + authz
│   └── suite/                     # 14-file project-documentation suite (was project-docs/)
│       ├── API.md
│       ├── AppFlow.md
│       ├── Deployment.md
│       ├── Design.md
│       ├── DOC-SUITE-MAP.md
│       ├── Glossary.md
│       ├── ImplementationPlan.md
│       ├── PRD.md
│       ├── RiskRegister.md
│       ├── Rules.md
│       ├── Schema.md
│       ├── SecurityAndCompliance.md
│       ├── TechSpec.md
│       ├── Testing.md
│       └── Tracker.md
├── pyproject.toml
├── pytest.ini
├── requirements.txt
├── scripts/
│   ├── migrations/001_percentile_tier_key.sql
│   └── seed_dev_db.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── api_football_fixtures.json
│   │   ├── fbref_league.html
│   │   ├── statsbomb_competitions.json
│   │   ├── statsbomb_events.json
│   │   ├── statsbomb_matches.json
│   │   ├── understat_api_players.json
│   │   └── understat_page.html
│   ├── test_anomaly.py
│   ├── test_api.py
│   ├── test_api_football.py
│   ├── test_base.py
│   ├── test_event_queries.py
│   ├── test_fbref.py
│   ├── test_idempotency.py
│   ├── test_index.py
│   ├── test_integration.py
│   ├── test_matrix_validation.py
│   ├── test_percentiles.py
│   ├── test_phase2_queries.py
│   ├── test_reconciliation.py
│   ├── test_sentences.py
│   ├── test_statsbomb.py
│   ├── test_tier_completeness.py
│   ├── test_trend.py
│   └── test_understat.py
└── web/
    ├── .dockerignore
    ├── .gitignore
    ├── Dockerfile
    ├── app/
    │   ├── (embed)/embed/radar/page.tsx
    │   ├── (embed)/embed/trend/page.tsx
    │   ├── changelog/page.tsx
    │   ├── clubs/[leagueSlug]/[teamSlug]/page.tsx
    │   ├── compare/og-image/route.tsx
    │   ├── compare/page.tsx
    │   ├── data-coverage/page.tsx
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── leagues/[leagueCode]/index/page.tsx
    │   ├── leagues/[leagueCode]/page.tsx
    │   ├── leagues/[leagueCode]/positions/[group]/page.tsx
    │   ├── leagues/[leagueCode]/stats/page.tsx
    │   ├── legal/privacy/page.tsx
    │   ├── legal/terms/page.tsx
    │   ├── methodology/page.tsx
    │   ├── not-found.tsx
    │   ├── page.tsx
    │   ├── players/[slug]/opengraph-image.tsx
    │   ├── players/[slug]/page.tsx
    │   ├── positions/page.tsx
    │   ├── pricing/page.tsx
    │   ├── trend/og-image/route.tsx
    │   └── trend/page.tsx
    ├── components/
    │   ├── Breadcrumbs.tsx
    │   ├── CompareTool.tsx
    │   ├── DatasetBanner.tsx
    │   ├── EmbedRadar.tsx
    │   ├── EmbedTrend.tsx
    │   ├── EventMaps.tsx
    │   ├── Footer.tsx
    │   ├── Header.tsx
    │   ├── KeyStats.tsx
    │   ├── LeaderboardTable.tsx
    │   ├── LegalDoc.tsx
    │   ├── PassMap.tsx
    │   ├── Pitch.tsx
    │   ├── RadarCard.tsx
    │   ├── RadarChart.tsx
    │   ├── RecencyLine.tsx
    │   ├── SearchCombobox.tsx
    │   ├── SharePanel.tsx
    │   ├── ShotMap.tsx
    │   ├── SimilarPlayers.tsx
    │   ├── SquadRadar.tsx
    │   ├── ThemeToggle.tsx
    │   ├── TrendCard.tsx
    │   ├── TrendChart.tsx
    │   └── TrendTool.tsx
    ├── e2e/
    │   ├── breakpoints.spec.ts
    │   └── core.spec.ts
    ├── lib/
    │   ├── api.ts
    │   ├── chartSvg.test.ts
    │   ├── chartSvg.ts
    │   ├── colors.ts
    │   ├── format.ts
    │   ├── ogRender.tsx
    │   ├── radar.ts
    │   ├── share.test.ts
    │   ├── share.ts
    │   ├── trend.ts
    │   └── types.ts
    ├── lighthouserc.json
    ├── next.config.mjs
    ├── package-lock.json
    ├── package.json
    ├── playwright.config.ts
    ├── scripts/e2e-server.sh
    ├── styles/tokens.css
    └── tsconfig.json
```

---

## 5. If You Only Read 5 Files, Read These

1. **`docs/CONSTITUTION.md`** — the governing rules. Every non-obvious decision in the
   codebase (append-only snapshots, coverage matrix, never-list, methodology-as-code) is
   explained here. Reading it first makes the rest of the code self-explanatory.
2. **`app/schema.sql`** — the canonical data model and the immutability/idempotency
   design in one file. All 10 tables with inline rationale comments.
3. **`app/orchestration/weekly_refresh.py`** — the pipeline job sequence
   (scrape → ingest → reconcile → anomaly → compute → publish). This is the spine of the
   product.
4. **`app/api/main.py`** — the full API surface and the "only the API touches the DB"
   boundary. Lists every route in one file.
5. **`web/lib/share.ts`** — the permalink/embed encoding that ties the whole sharing
   layer together (pure, zero-import, tested). Explains how the URL state works.

---

## 6. Exhaustive File-by-File Breakdown

### 6.1 Root files

#### `README.md`
- **Type**: Markdown documentation.
- **Purpose**: Human entry point: what Statlas is, quick start, usage, config, testing,
  deployment, roadmap, FAQ, license. *(Explicit — polished per the README enhancement
  blueprint on 2026-08-14.)*
- **Key content**: 3-command quick start, route table, env-var table, 104 pytest / 12 node
  tests, Playwright + Lighthouse CI notes, AGPL-3.0 license.
- **Side effects**: none.

#### `LICENSE`
- **Type**: Legal text.
- **Purpose**: GNU AGPL v3.0 full text. The license is chosen deliberately: "if you modify
  and run this software on a network server, you must make the modified source available
  to its users" *(explicit — README License section)*.

#### `requirements.txt`
- **Type**: Python dependency manifest (no lock file; version floors).
- **Purpose**: All backend deps: `requests`, `beautifulsoup4`, `SQLAlchemy`,
  `psycopg2-binary`, `fastapi`, `uvicorn`, `pydantic`, `pytest`, `ruff`, plus closeout
  additions `pip-audit`, `gitleaks` (via CI action, not here).
- **Note** *(explicit)*: production and development share one manifest; no packaging
  metadata exists (pyproject.toml is ruff config only).

#### `pyproject.toml`
- **Type**: ruff + tooling config.
- **Purpose**: Enforces the lint rule set so CI and local behave identically:
  `select = ["E4", "E7", "E9", "F", "I", "DTZ"]` *(explicit — DTZ added in closeout C2
  for the timezone policy)*. `target-version = "py310"` (code floor; dev/CI run 3.14).
  Per-file ignore: E402 for `scripts/seed_dev_db.py` (env set before import — the
  script's point).
- **Deferred rules** *(explicit — commented)*: UP037, BLE001, SIM*, B017 are documented
  but not enforced.

#### `pytest.ini`
- **Type**: pytest config. Sets `pythonpath = .` and `testpaths = tests`.

#### `.gitignore` / `web/.gitignore`
- **Type**: Git ignore rules.
- **Purpose**: Excludes `__pycache__/`, `.venv/`, `.cache/`, `*.db`, `node_modules/`,
  `.next/`, `.env*`, test/perf artifacts (`test-results/`, `playwright-report/`,
  `lhci-reports/`, `.lighthouseci/`).
- **Notable exception** *(explicit — added closeout)*: `data/*` is ignored but
  `!data/coverage_matrix.json` is tracked, because Constitution §3 designates the
  coverage matrix as the machine-readable single source of truth and CI validates it.

#### `.dockerignore` / `web/.dockerignore`
- **Type**: Build-context exclusion.
- **Purpose** (root): keeps the API image lean — excludes `.venv`, caches, `data/*.db`,
  `web/`, `node_modules`, `.next`, docs, `.github`, `.env*` (keeps `.env.example`).
- **Purpose** (web): excludes `node_modules`, `.next`, `.git`, `*.tsbuildinfo`,
  `next-env.d.ts`.

#### `.gitattributes`
- **Type**: Git attributes. Sets `* text=auto` and explicit `eol=lf` for source files
  (py, ts, tsx, mjs, js, json, css, md, sql, html, txt) — enforces LF line endings
  across platforms.

#### `.env.example`
- **Type**: Environment template (tracked; no secrets).
- **Purpose**: Documents every env var with defaults and inline rationale. See §9 for
  the full table.

### 6.2 `app/` — Python backend

#### `app/__init__.py`
- Empty package marker.

#### `app/config.py`
- **Type**: Configuration loader.
- **Purpose**: Single place where locked numbers from Phase 0 docs enter code.
- **Key exports** *(explicit)*:
  - `load_registry()` (lru_cached) — reads `app/config/metric_registry.json` (methodology-as-code).
  - `load_tiers()` (lru_cached) — reads `app/config/tiers.json`.
  - `env()`, `env_float()`, `env_int()`, `env_bool()` helpers.
  - `class Settings` — runtime settings with compliance defaults: `database_url` (None →
    SQLite), `user_agent` (StatlasAnalytics/0.1 …), `fbref_delay_seconds=10.0`,
    `fbref_jitter_seconds=2.0`, `understat_delay_seconds=5.0`,
    `api_football_delay_seconds=2.0`, `api_football_daily_budget=80`,
    `api_football_key`, `cache_dir=".cache"`, `enrich_positions=False`,
    `log_level=INFO`, `dataset_mode="fixture-demo"`, `dataset_note`.
  - `get_settings()` / `set_settings()` (test hook).
- **Side effects**: reads env vars; caches registry/tiers globally.

#### `app/db.py`
- **Type**: Database engine/session management.
- **Key exports**: `get_engine()`, `get_session_factory()`, `session_scope()`,
  `create_schema()`.
- **Logic**: SQLite in-memory with `StaticPool` + `check_same_thread=False` when
  `DATABASE_URL` unset; otherwise a pooled engine with `pool_pre_ping=True`.
  `create_schema()` builds tables from ORM models (for tests/dev; production DDL lives
  in `schema.sql`).
- **Side effects**: engine/session singleton globals; DB connection; table creation.
- **Inbound deps**: imported by `app/cli.py`, `app/api/main.py`, tests, seed script.

#### `app/models.py` (689 lines)
- **Type**: SQLAlchemy ORM models — the code-side mirror of `schema.sql`.
- **Key exports**: `Base` (DeclarativeBase), enums, and 15 model classes:
  `League`, `Team`, `Player`, `PlayerNameAlias`, `StatSnapshot`, `PercentileSnapshot`,
  `MatchEvent`, `DataCoverage`, `IngestionAnomaly`, `ReconciliationQueue`, `Fixture`,
  `User`, `SessionToken`, `Subscription`, `ApiKey`, `WebhookEvent`, `AssistantQuota`,
  plus the Phase 7 workspace set: `Shortlist`, `ShortlistEntry`, `EntryNote`, `EntryTag`,
  `StatusHistory`.
- **Notable logic** *(explicit)*:
  - Enums declared `native_enum=True` (the closeout C3 parity fix) — Postgres gets real
    `CREATE TYPE` enums; SQLite falls back to VARCHAR+CHECK automatically.
  - `StatSnapshot` natural-key unique constraint
    `(player_id, team_id, league_id, season, source, scrape_date)` — idempotency.
  - `PercentileSnapshot` unique key `(stat_snapshot_id, metric_name, league_tier)` —
    the tier dimension added in closeout C1 (cross-tier transfer fix).
  - `DataCoverage` CHECK: `league_id IS NOT NULL OR source = 'statsbomb'`.
  - Phase 7: `ShortlistEntry` UNIQUE `(shortlist_id, player_id)`; soft-delete columns
    (`removed_at`/`deleted_at`) on entries/shortlists; `StatusHistory.from_status` NULL
    on the initial creation row. Rules enforced in `queries/workspace_queries.py`.
- **Side effects**: none at import (schema creation happens in `db.create_schema`).

#### `app/schema.sql` (384 lines)
- **Type**: Canonical PostgreSQL DDL (the source of truth for production).
- **Purpose**: 16 tables + 8 enums + indexes + the design-principles header comment
  (append-only, versioned by scrape date, natural keys for idempotency, publish gate,
  anomaly gate, coverage matrix).
- **Notable**: comments document every immutability decision inline. Phase 7 adds
  `entry_status`/`entry_priority` enums and the workspace tables (shortlists,
  shortlist_entries, entry_notes, entry_tags, status_history) with soft-delete columns
  and the `(shortlist_id, player_id)` unique constraint. Applied by the postgres
  compose image on fresh volumes and by `scripts/migrations/001_*` for existing
  volumes.

### 6.3 `app/api/` — FastAPI layer

#### `app/api/main.py` (357 lines)
- **Type**: FastAPI application + routes.
- **Purpose**: The versioned `/api/v1` surface — the ONLY data-access layer the web app
  talks to.
- **Key exports**: `app` (FastAPI), `ErrorDetail` (Pydantic), `_with_session()` helper,
  and all route handlers.
- **Routes** (see §8 for full table): health, meta, leagues (+detail, +stats),
  leaderboard, players/search, players/by-slug, players/{id}/similar, players/{id}/trend,
  players/{id}/events (+matches/shots/passes), clubs/{league}/{team}, coverage, positions,
  methodology.
- **Notable logic**: CORS restricted to localhost:3000 (GET only, no credentials);
  `ValueError` → 400 via exception handler; route params validated (`VALID_POSITIONS`,
  tier whitelist, `sort_by` whitelist); 404s raised as `HTTPException`.
- **Side effects**: opens DB sessions per request via `session_scope()`; network none.
- **Config read**: `get_settings().dataset_mode/note` (meta endpoint).

#### `app/api/player_view.py` (163 lines)
- **Type**: Player payload builders.
- **Purpose**: Build the ONE aggregate payload the SSR player profile consumes (single
  round trip). Resolves per-axis display semantics here (never in the renderer):
  `qualified | below_floor | unranked_pool | no_data`.
- **Key exports**: `build_player_payload(db, player_id)`, `build_radar_axes(...)`,
  `has_player_event_data(...)`, `_age_on(...)`, `_axis_status(...)`.
- **Notable logic**: `_axis_status` orders checks — percentile present → qualified; no
  raw → no_data; counter floor unmet (`REGISTRY_FLOOR_KEYS`) or minutes <
  `display_floor_minutes` → below_floor; else unranked_pool. Age computed from stored
  DOB vs snapshot date (UTC date — timezone policy). `photo` is always `None` (honest
  placeholder — no licensed imagery).
- **Inbound deps**: called by `main.py` `player_by_slug`.

#### `app/api/registry_view.py` (133 lines)
- **Type**: Public metric-metadata view.
- **Purpose**: Single source for metric names, units, definitions, directions,
  null-vs-zero policy, floors — the frontend never hardcodes any of it
  (methodology-as-code).
- **Key exports**: `UNITS`, `DEFINITIONS`, `POSITION_LABELS`, `POSITION_PLURALS`,
  `TIER_LABELS`, `metric_meta(registry, mid)`, `public_meta()`.
- **Notable**: 16 metric definitions written out (e.g. xG tier-1 Understat vs tiers 2–3
  FBref "one model per comparison group").
- **Inbound deps**: used by `main.py` (meta/methodology/positions) and
  `queries/trend_queries.py` (`_metric_meta`).

### 6.4 `app/compute/` — computation jobs

#### `app/compute/percentiles.py`
- **Type**: Percentile + index computation job.
- **Purpose**: For each qualifying player (>= 900 minutes) in each
  {position_group, league_tier} cohort, compute the fractional-rank percentile for every
  metric; results written as NEW rows, never updates.
- **Key exports**: `compute_percentiles()`, `fractional_rank()`, `compute_index_score()`,
  `resolve_metric_value()`, `tier_completeness()`, `latest_snapshot_date()`,
  `REGISTRY_FLOOR_KEYS`, `MIN_REQUIRED_METRICS`, `PercentileReport` dataclass.
- **Notable logic** *(explicit)*:
  - `P = (B + 0.5E)/N * 100`, peers-only counting (own value excluded), direction-aware
    (lower-is-better inverts the comparison).
  - Value resolution honors per-metric, per-tier source precedence from the registry.
  - Idempotency: precomputed sets of snapshots-with-rows (a live query would autoflush
    mid-loop and skip every player).
  - **Tier-completeness gate** (closeout C1): `require_tier_completeness=True` withholds
    a tier unless EVERY league in it is ingested (coverage matrix as arbiter).
  - Cross-tier transfer fix: `snapshots_by_tier` keys by (player, source) PER TIER.
- **Side effects**: DB writes (commit at end).

#### `app/compute/index.py`
- **Type**: Statlas Index pure calculation + verifier.
- **Purpose**: `Index = Σ(w_i/W_present)·p_i` — weighted mean of metric percentiles,
  weights renormalized over present metrics; not computed when too few metrics present
  (>= 8 of 12 outfield, >= 3 of 4 GK).
- **Key exports**: `compute_index()`, `verify_index_consistency()`.
- **Notable**: `verify_index_consistency` re-derives every stored index row from metric
  rows and returns discrepancies (fail-loudly to the weekly refresh).
- **Inbound**: `compute_index_score` reused from `percentiles.py` (single source of truth).

#### `app/compute/anomaly_check.py`
- **Type**: Anomaly detection.
- **Purpose**: Two passes — (1) `check_snapshot_bounds`: every metric vs registry bounds
  (e.g. pass % in [0,100], no negative minutes, no impossible values); violations become
  `ingestion_anomalies` rows and the snapshot flips to `flagged`. Also fails loudly on an
  FBref snapshot with minutes but ZERO extracted registry metrics (schema drift), and
  flags undocumented metric keys. (2) `cross_source_spot_check`: for Tier-1 players in
  both FBref and Understat, compares overlapping metrics (xG, shots) with absolute +
  relative tolerances; divergence flags carry `stat_snapshot_id=NULL` (the anomaly is
  about the relationship).
- **Key exports**: `check_snapshot_bounds()`, `cross_source_spot_check()`,
  `blocked_player_ids()`, `resolve_anomaly()`.
- **Notable**: `blocked_player_ids` is intentionally NOT date-scoped — an unresolved
  anomaly keeps the player out of every future run until a human resolves it.
  `resolve_anomaly` is the explicit human override ("never silently published" =
  "must be reviewed").

### 6.5 `app/config/` — locked configuration

#### `app/config/metric_registry.json`
- **Type**: JSON config (methodology-as-code, generated from methodology.md).
- **Content**: `schema_version`, `qualifying_minutes=900`, `display_floor_minutes=180`,
  `min_pool_size`, `index_metric_id="si_index"`, `position_groups` (8),
  `outfield_metrics` (12), `gk_metrics` (4), `metrics` (16 entries: name, kind, direction,
  fbref/understat source mapping + candidates, bounds, display_floor, null_vs_zero),
  `position_weights` (8 rows summing to 1.0), `anomaly` (field_bounds, cross_source config).
- **Validated by**: `tests/test_matrix_validation.py` (uniqueness, weights sum to 1,
  bounds sanity).

#### `app/config/tiers.json`
- **Type**: JSON config (from percentile-rules.md).
- **Content**: `tiers` (tier_1 = Big-5, tier_2 = 9 leagues, tier_3 = 5 second divisions),
  `leagues` map slug → {name, country, tier, external_ids {fbref_comp, understat,
  api_football}}. Note: ids must be verified against live sources at first real scrape.

### 6.6 `app/orchestration/` — pipeline jobs

#### `app/orchestration/weekly_refresh.py`
- **Type**: Orchestration job.
- **Purpose**: The fixed weekly job sequence:
  `scrape → ingest → reconcile → anomaly-check → percentiles+index → publish`
  (every Wednesday 03:00 UTC per percentile-rules.md §3).
- **Key exports**: `run_weekly_refresh()`, `RefreshReport` dataclass,
  `ensure_league_catalog()`, `get_or_create_team()`, `resolve_player_for_record()`,
  `ingest_source_records()`, `update_coverage()`, `publish_run()`, `store_fixtures()`.
- **Notable logic** *(explicit)*:
  - Sources injectable (tests pass fakes; CLI passes real sources).
  - Understat only scraped for `tier_1` leagues (the documented xG model rule).
  - Idempotency by natural key; `publish_run` flips `is_published` only for THIS run's
    `computed_date` rows.
  - Optional layers: StatsBomb sync + `link_match_events` (Phase 3), API-Football
    fixtures.
  - Tier-completeness gate wired: production runs pass `require_tier_completeness=True`.
- **Side effects**: DB writes; network via injected sources.

#### `app/orchestration/event_link.py`
- **Type**: StatsBomb event → player linking.
- **Purpose**: Resolve `match_events.player_id` (NULL after sync) to canonical players by
  **exact normalized name** — never a fuzzy best-guess join. Zero candidates → stays
  unmatched; two or more → logged ambiguous and left NULL for human review.
- **Key exports**: `link_match_events()`, `EventLinkReport`.
- **Notable**: name indexes built once per run (O(1) lookups per event); idempotent.

### 6.7 `app/queries/` — data-access layer

> All query functions take a `Session` as the first argument and return plain dicts.
> They only read `is_published=true` rows (the anomaly/publish gate).

#### `app/queries/player_queries.py` (295 lines)
- **Purpose**: Player profile page data.
- **Key exports**: `get_player_profile()`, `get_player_percentiles()`,
  `slugify_name()`, `player_slug_map()`, `get_player_slug()`, `resolve_player_slug()`,
  `search_players()`, `get_player_raw_stats()`.
- **Notable logic**: slug rules — name slug, `-{club-slug}` on collision, `-{id}` last
  resort; `resolve_player_slug` returns `canonical: False` for non-canonical forms
  (caller 301s); search matches canonical names AND aliases (reconciliation spelling
  store) with prefix-match ranking; `get_player_percentiles` documents the blocking
  semantics (a blocked player shows last cleanly published values, not retroactive
  unpublish).

#### `app/queries/leaderboard_queries.py` (198 lines)
- **Purpose**: Published percentile/index leaderboard rows.
- **Key exports**: `get_leaderboard()`, `get_leaderboard_filtered()`.
- **Notable**: latest-snapshot-per-player rule; direction-aware sorting ('lower is
  better' ascends); server-side column sorting + pagination (`has_more`).

#### `app/queries/league_queries.py` (201 lines)
- **Purpose**: League catalog, raw-stats table, teams.
- **Key exports**: `get_league_catalog()`, `get_league_detail()`,
  `get_league_stats_table()`, `get_league_teams()`.
- **Notable**: catalog enriched from `data_coverage`; stats table excludes
  `blocked_player_ids` and resolves per-metric display floors (`_floor_met` — minutes
  floors and counter floors via `REGISTRY_FLOOR_KEYS`); `SEASON_FALLBACK="2025-26"`.

#### `app/queries/team_queries.py` (163 lines)
- **Purpose**: Team profile payloads.
- **Key exports**: `get_team_profile()`, `_roster()`, `_squad_radar()`.
- **Notable**: roster keyed by snapshot's team (honest mid-season transfer placement);
  squad radar = average published percentile per metric across qualifying players,
  `None` when < 5 qualified (UI renders explicit empty state).

#### `app/queries/trend_queries.py` (255 lines)
- **Purpose**: Snapshot-history trends (Phase 3).
- **Key exports**: `get_player_trend()`, `TREND_WINDOWS=(5,10)`, `DEFAULT_WINDOW=5`,
  `MIN_TREND_SNAPSHOTS=5`, `GRANULARITY_NOTE`.
- **Notable honesty rules** *(explicit)*: granularity="snapshot" (never per-match);
  gaps measured against the league/season cohort calendar (dashed breaks, never
  interpolation); flagged snapshots marked `anomaly=true`; transfers derived from real
  team changes; values resolved with the same registry precedence as the percentile job.
  Timezone: group keys normalized to UTC then tzinfo dropped explicitly (policy §5).

#### `app/queries/event_queries.py` (265 lines)
- **Purpose**: Shot/pass event data, coverage-gated (Phase 3).
- **Key exports**: `get_player_event_coverage()`, `get_player_event_matches()`,
  `get_player_events()`, `get_statsbomb_competitions()`, `is_progressive_pass()`,
  `competition_label()`, `STATSBOMB_COMPETITION_NAMES`.
- **Notable**: coverage check is the FIRST step — no coverage row → no data, period;
  `is_progressive_pass`: end_x - start_x >= 10 or entry into the penalty area (x >= 102)
  on the StatsBomb 120×80 pitch; attribution required by consumers (data-compliance §3).

#### `app/queries/coverage_queries.py`
- **Purpose**: The coverage-matrix arbiter.
- **Key exports**: `get_data_coverage()`, `has_source_coverage()`.
- **Notable**: `has_source_coverage` is the single check map UIs must pass — row exists,
  status active (optional), season in `seasons_available`.

#### `app/queries/workspace_queries.py` (689 lines)
- **Purpose**: Phase 7 scouting workspace — shortlists, entries, notes, tags, history.
- **Key exports**: `list_shortlists`, `create_shortlist`, `get_shortlist_detail`,
  `add_player_to_shortlist`, `update_entry_status`, `set_entry_priority`,
  `add_entry_note`, `add_entry_tag`, `remove_entry_tag`, `remove_entry`,
  `delete_shortlist`, `get_shortlist_memberships`, `get_user_tag_suggestions`,
  `validate_transition`, pipeline constants, and the domain exceptions
  (`ShortlistNotFound`, `PlayerNotFound`, `InvalidStatusTransition`, `DuplicateEntry`,
  `WorkspaceLimitExceeded`).
- **Notable**: ownership verified on EVERY read/write (foreign/missing →
  `ShortlistNotFound` → HTTP 404, never an existence-leaking 403); transition rules
  from docs/product/scouting-pipeline.md (forward skips + backward moves allowed,
  rejected exits only via monitoring, signed terminal, same-status no-op); soft delete
  preserves notes/tags/history; Free tier caps (1 shortlist / 10 entries, pricing.json)
  raise `WorkspaceLimitExceeded` with honest upsell copy; `get_shortlist_detail` joins
  player summary + latest published index in a handful of queries (no N+1).

#### `app/queries/sentences.py` (137 lines)
- **Purpose**: Data-driven profile sentences (Constitution §5, Never-List #4).
- **Key exports**: `build_profile_sentence()`, `ordinal()`.
- **Notable**: template "{name} ranks in the {Nth} percentile for {metric} among {Tier N}
  {position-plurals} this season" populated from real published data; boundary cases:
  pending qualification (with real minutes), no snapshot (coverage-honest copy),
  percentile < 0.5 ("bottom of the group"), index sentence appended when present.

#### `app/queries/similar_players.py` (319 lines)
- **Purpose**: Real nearest-neighbour computation (Phase 2 B4) + the Phase 6 explanation
  layer on top of it.
- **Key exports**: `get_similar_players()`, `build_similarity_explanation()`,
  `_cosine_with_components()`, `_cosine_similarity()`, `MIN_SHARED_METRICS=5`,
  `MATCHED_STRENGTH_MIN_PERCENTILE=70`, `MATCHED_STRENGTH_MAX_DIFF=20`,
  `KEY_DIFFERENCE_MIN_GAP=25`, `MAX_EXPLAINED_ITEMS=3`.
- **Notable**: cosine similarity over the shared published-percentile subset within the
  same {position_group, league_tier} cohort; absent metrics excluded from that pair
  (never a zero); fewer than 5 shared metrics → not considered; `sim <= 0` filtered.
  Each result carries an `explanation`: matched strengths are the metrics that
  contributed most to the cosine score where both players rank >= 70th and sit within
  20 percentile points; key differences are the largest gaps (>= 25 points) with the
  stronger player stated. The decomposition reuses the same dot product/norms as the
  ranking (explanation cannot diverge from the score); excluded metrics carry their
  registry display name so the UI can name them (similarity-explanation-method.md).

### 6.8 `app/sources/` — data-source adapters

#### `app/sources/base.py` (238 lines)
- **Type**: Shared source infrastructure.
- **Key exports**: `StatsSource` (ABC), `RawPlayerStatRecord` + `FixtureRecord`
  dataclasses, `RateLimiter`, `HttpCache`, `fetch_with_retry()`, `backoff_delays()`,
  error classes `SourceError` / `SchemaChangedError` / `BudgetExhaustedError`.
- **Notable logic**:
  - `RateLimiter.wait()` enforces declared delay BETWEEN requests (interval + jitter).
  - `HttpCache` — SHA-256-keyed JSON cache under `STATLAS_CACHE_DIR`, 7-day TTL;
    cache never takes the pipeline down (writes logged, reads fail soft).
  - `fetch_with_retry`: backoff schedule 1s→2s→4s→8s→16s→30s→60s cap (finite list —
    the closeout A fix for an infinite-loop bug); 429/503 → backoff+retry; **403 → hard
    abort**; POST bypasses cache (stateful payloads).
  - `backoff_delays()` documented: snaps the 32s doubling step to the declared 30s.

#### `app/sources/fbref.py` (448 lines)
- **Type**: FBref scraper (primary per-90 source).
- **Compliance posture** *(explicit)*: 1 req / 10s ± 2s jitter (`FBREF_DELAY_SECONDS`),
  40% below FBref's documented ceiling; descriptive UA; aggressive caching; backoff on
  429/503, abort on 403.
- **Key exports**: `FBrefSource`, `parse_fbref_table()`, `fbref_table_id()`,
  `canonical_season_to_fbref()`, `FBrefSchemaChangedError`, `FBREF_TABLES`,
  `POSITION_GROUP_MAP`.
- **Notable logic**: one request per league-season page contains all 9 stat tables;
  combined header names ("<group> <column>") disambiguate duplicated columns (e.g. xG in
  totals vs per-90); rows joined across tables by FBref player id (fallback name+team);
  transferred-player aggregate rows ("2 teams" etc.) skipped; missing required tables →
  `FBrefSchemaChangedError` (fail loudly); per-90 derivation `total/minutes*90`;
  counter floor keys written as `_cmp_attempts` etc.; GK metrics handled via
  `gk_metrics`; derived metric `psxg_minus_ga` computed from inputs.
- **Known limitation** *(explicit — docstring + validation log)*: FBref returns 403 to
  this scraper from the build environment; production-readiness requires a credentialed
  run.

#### `app/sources/understat.py` (205 lines)
- **Type**: Understat xG/xA source (Big-5 / Tier 1 only).
- **Compliance posture**: 1 req / 5s; robots `Disallow: /` noted as revocable; derived
  per-90 values only.
- **Key exports**: `UnderstatSource`, `extract_players_json()`, `UnderstatSchemaChangedError`,
  `METRIC_KEY_MAP` (xG/xA/shots/key_passes/goals → registry ids).
- **Notable logic**: primary extraction from embedded `playersDataObject` JSON;
  **fallback (2026 live drift fix)** to POST `main/getPlayersStats/` when the embedded
  payload is gone; both paths produce the same list-of-dicts shape; loud
  `UnderstatSchemaChangedError` only if both fail; per-90 derivation from totals.

#### `app/sources/statsbomb.py` (281 lines)
- **Type**: StatsBomb Open Data sync (periodic, not live scrape).
- **Key exports**: `StatsBombOpenDataSource`, `sync_competition()`,
  `build_event_rows()`, `fetch_competitions()`, `matches_url()`, `events_url()`.
- **Notable logic**: pulls JSON from `raw.githubusercontent.com/hudl/open-data`; writes
  `match_events` rows with `player_id=NULL` (linking happens later in
  `event_link.py`); upserts `data_coverage` rows `statsbomb:<comp>:<season>` —
  coverage honesty; **live-drift fix (2026)** — `competitions.json` is now a flat list
  of competition-season pairs; both old nested and new flat shapes supported;
  `extra` payload carries shot xG/body_part/technique and pass end coords/type/recipient.
- **Compliance**: attribution (StatsBomb logo + source statement) treated as a UI
  requirement.

#### `app/sources/api_football.py` (177 lines)
- **Type**: API-Football fixtures/live layer.
- **Compliance posture**: 80 req/day budget (20% headroom under the 100/day published
  figure); 1 req / 2s; raw payloads never republished.
- **Key exports**: `APIFootballSource`, `FileBackedBudget`, `parse_fixtures()`,
  `build_url()`, `canonical_season_to_year()`.
- **Notable logic**: `FileBackedBudget` persisted to disk, resets on UTC date change
  (timezone policy — two servers agree on the day boundary); `acquire()` raises
  `BudgetExhaustedError` — the hard stop, never a silent mid-run failure.

### 6.9 `scripts/` — dev/ops scripts

#### `scripts/seed_dev_db.py` (715 lines)
- **Type**: Dev-database seed script.
- **Purpose**: Builds `data/dev.db` through the REAL pipeline (orchestration, parsers,
  reconciliation, anomaly checks, percentile/index computation, publishing) against
  labeled fixtures + deterministic synthetic leagues. Premier League = real FBref parser
  over `tests/fixtures/fbref_league.html` (37 players, Man City + Liverpool) + real
  Understat parser over `understat_page.html`; other leagues = seeded-RNG synthetic
  records with fictional names and real club names.
- **Notable** *(explicit)*: 7 weekly scrape dates with deterministic per-player drift,
  one deliberately missing snapshot (gap demo), one mid-season transfer (annotation
  demo), synthetic StatsBomb event data for Haaland/Salah under real coverage rows,
  exports `data/coverage_matrix.json`. Sets `DATABASE_URL` via `os.environ.setdefault`
  BEFORE importing db (hence the E402 per-file ignore). NEVER point at production.
- **Side effects**: deletes/rebuilds `data/dev.db`; writes `data/coverage_matrix.json`.

#### `scripts/migrations/001_percentile_tier_key.sql`
- **Type**: PostgreSQL migration (closeout C1).
- **Purpose**: Drops the old `uq_percentile_snapshot_metric` constraint and re-adds
  `uq_percentile_snapshot_metric_tier UNIQUE (stat_snapshot_id, metric_name, league_tier)`.
  Idempotent (DROP IF EXISTS + ADD). Apply with `psql $DATABASE_URL -f ...` to existing
  volumes; fresh volumes get it from `schema.sql`.

### 6.10 `tests/` — test suite

> 185 tests total, all on in-memory SQLite (no network). `tests/conftest.py` provides
> the `db` fixture (ORM-built in-memory engine), `premier_league`, `small_pool`
> (registry overrides `min_pool_size=5`), `fixtures_dir()`, and `compute_and_publish()`
> (compute + publish — the query layer serves published rows only).

| File | Lines | What it tests |
| --- | --- | --- |
| `test_anomaly.py` | — | Bounds checking, flagged status, unresolved dedupe, schema-drift guard, cross-source flags, `blocked_player_ids`, `resolve_anomaly` |
| `test_api.py` | 155 | API endpoints against a seeded session (health/meta/leagues/leaderboard/players/coverage/positions), 404s, validation |
| `test_api_football.py` | — | `parse_fixtures`, `FileBackedBudget` (day rollover, exhaustion), URL builders |
| `test_base.py` | — | `backoff_delays` schedule (finite, ends at cap), rate limiter spacing, cache TTL |
| `test_event_queries.py` | 197 | Coverage gating (no row → no data; active row unlocks; failed blocks), progressive-pass rule, competition labels |
| `test_fbref.py` | 111 | Parser over fixture HTML: metric extraction, combined headers, id join, schema-change raises loudly |
| `test_idempotency.py` | — | Re-running weekly refresh does not duplicate rows; coverage upsert idempotent |
| `test_index.py` | — | Index formula vs hand-calculated example, missing-metric renormalization, GK weights, verifier |
| `test_integration.py` | 211 | Full pipeline end-to-end on fixtures; DB ends in expected state |
| `test_matrix_validation.py` | 189 | Constitution §3 CI gate: registry schema/uniqueness/weights-sum-to-1, tiers consistency, coverage-matrix well-formed, UI claims ≤ matrix, dataset banner honesty |
| `test_percentiles.py` | 182 | Fractional-rank math, direction handling, small pools, idempotent re-run, precedence |
| `test_phase2_queries.py` | 195 | Profile payload, slug resolution, search ranking, leaderboard filters, sentences |
| `test_reconciliation.py` | 112 | Normalization (accents, suffixes, punctuation), exact-match tie-breakers, queue + resolve flow |
| `test_sentences.py` | 157 | Ordinals, pluralization, boundary states (0 percentile, tiny pool, no data) |
| `test_statsbomb.py` | 68 | Sync stores events + coverage; no duplicate events; both competitions.json shapes |
| `test_tier_completeness.py` | 229 | §1.4 gate withholds incomplete tiers; cross-tier-transfer percentile keys don't collide |
| `test_trend.py` | 223 | Trend points, gaps vs cohort calendar, transfer events, windowing, insufficient state, timezone key handling |
| `test_workspace.py` | 707 | Phase 7 workspace: CRUD, pipeline transitions (valid + explicitly invalid), cross-user 404s on read/write (never existence-leaking 403), duplicate-add rejection, soft-delete audit preservation, free-tier caps with honest upsell, own-only tag suggestions, multi-step status-history audit, API-level auth + error mapping |
| `test_understat.py` | 121 | Embedded-JSON extraction, POST fallback (live-drift fixture), loud schema error |

**Fixtures** (`tests/fixtures/`): `fbref_league.html` (19 KB real-shaped FBref page),
`understat_page.html`, `understat_api_players.json` (real live-response capture),
`statsbomb_competitions.json`, `statsbomb_matches.json`, `statsbomb_events.json`,
`api_football_fixtures.json`.

### 6.11 `web/` — Next.js frontend

#### `web/lib/` — pure/shared modules

- **`types.ts`** — TypeScript types mirroring every API payload: `Meta`, `MetricMeta`,
  `PositionGroupMeta`, `Axis`, `PlayerPayload`, `LeaderboardResponse`, `SearchResult`,
  `LeagueSummary`, `CoveragePayload`, `TeamPayload`, `TrendPayload`, `EventCoverage`,
  `ShotEvent`, `PassEvent`, etc.
- **`api.ts`** — fetch wrapper: `API_URL` selects `STATLAS_API_URL` (server) vs
  `NEXT_PUBLIC_STATLAS_API_URL` (browser); `ApiError` with status; `qs()` helper;
  `api.*` object with one method per endpoint (all `cache: "no-store"`).
- **`share.ts`** — pure permalink/embed logic (zero imports; runs in browser, server,
  and node --test). `encodeRadarQuery`/`decodeRadarQuery`, `encodeTrendQuery`/
  `decodeTrendQuery`, `decodeShareConfig`, `sharePageUrl`, `ogImageUrl`,
  `embedPageUrl`, `buildEmbedCode` (responsive lazy iframe + unstrippable attribution),
  `socialShareUrls`, `DEFAULT_TREND_METRICS`. Limits: 4 radar players, 3 trend players,
  windows 5/10, `v=1` config version.
- **`radar.ts`** — `buildRadarPlayers(payloads)`: canonical axis union ordered by first
  player; fills missing axes as `no_data`. Shared by compare tool and embed widget.
- **`trend.ts`** — `fetchTrendLines()`: fetches one trend per (player, metric) combo via
  `Promise.all`, maps to chart line format (color by index, dash by metric index),
  aggregates `insufficient`/`available`/`minSnapshots`/`granularityNote`.
- **`colors.ts`** — `PLAYER_COLORS` (Okabe-Ito categorical: blue/vermillion/green/sky),
  `METRIC_DASHES` (solid/dash/dot); `playerColor(index)`, `metricDash(index)`. Color is
  never the only signal.
- **`format.ts`** — `formatDate`, `formatDateTime` (UTC label), `formatNumber`,
  `formatPercentile` ("p37"), `ordinal`, `initials`, `percentileBand` (text-safe ramp
  tokens — chart-fill ramp fails WCAG AA as text), `positionGroupLabel`, `tierLabel`.
- **`chartSvg.ts`** — pure SVG builders for OG images (zero imports): `radarChartSvg()`,
  `trendChartSvg()` (both with rings/gridlines/gap dashes/transfer markers), `svgDataUrl()`
  (base64, not percent-encoding — satori's `<img>` handling), `OG_PLAYER_COLORS`,
  `OG_METRIC_DASHES`, dark-theme token constants documented inline.
- **`ogRender.tsx`** — `renderOgCard()`: wraps a chart SVG in the dark Statlas card with
  wordmark via `next/og` `ImageResponse` (1200×630, cacheable 1h/86400s).
- **`chartSvg.test.ts` / `share.test.ts`** — node --test quality gates: permalink
  round-trip and OG-image-contains-real-values.

#### `web/components/` — React components

| File | Purpose / notable behavior |
| --- | --- |
| `RadarChart.tsx` (375) | SVG radar: 1–4 overlaid players, percentile/raw mode, ring gridlines, per-axis tooltips (metric name + unit + definition), accessible data-table alternative (visually-hidden), skeleton polygon loading state, insufficient-data note; describes itself via `describe()` for screen readers |
| `RadarCard.tsx` (153) | Card wrapper around RadarChart with player add/remove chips, mode toggle, share panel wiring; `MAX_PLAYERS = 4` |
| `TrendChart.tsx` (415) | SVG time-series: dashed gap segments with break markers, anomaly warning rings, transfer annotations, numeric labels on every value |
| `TrendCard.tsx` (163) | Trend chart card with metric/player/mode controls + share panel |
| `CompareTool.tsx` (168) | `/compare` client tool: URL-state driven (encode/decode radar query), add/remove players, mode toggle, SharePanel |
| `TrendTool.tsx` (301) | `/trend` client tool: player × metric multi-select, window selector (5/10), mode toggle |
| `SearchCombobox.tsx` (195) | Accessible combobox: debounced search-as-you-type against `/players/search`, arrow-key navigation, Enter select, loading/empty/error states, abort of stale requests |
| `ShotMap.tsx` (414) / `PassMap.tsx` (400) | StatsBomb pitch maps; outcomes by shape AND color; xG-scaled shot size; directional pass arrows with progressive filter; data-table toggle; StatsBomb attribution |
| `Pitch.tsx` (71) | `soccerToPitch()` coordinate mapping + SVG pitch (120×80 StatsBomb coords) |
| `EventMaps.tsx` (146) | Coverage-gated entry point: renders ShotMap/PassMap only when `has_event_data`, else the honest "no coverage" note |
| `EmbedRadar.tsx` (72) / `EmbedTrend.tsx` (98) | iframe widget pages — bare frames, no site banner, Powered-by-Statlas attribution inside |
| `SharePanel.tsx` (144) | Copy link / copy embed / X + LinkedIn intents with feedback states; OG-image preview |
| `SimilarPlayers.tsx` (216) | Fetches + renders nearest neighbours with the stated similarity basis; each row's disclosure shows the real "why" (matched strengths with up indicators, key differences with the stronger player named, honest no-differences / missing-data notes) — all states: loading skeleton, empty, retry-capable error; per-row Save-to-shortlist (Phase 7) |
| `AddToShortlist.tsx` (255) | Lazy "Add to shortlist" everywhere players appear (profile header, leaderboard rows, similar results): zero requests until first click; real selector with inline create when multiple shortlists; marks already-saved players; signed-out → sign-in link; free-cap → honest upsell; success → link to the shortlist |
| `KeyStats.tsx` (50) | Key-stat summary table from real raw snapshot values + percentile chips + status hints |
| `SquadRadar.tsx` (60) | Squad-average radar with N + empty state when < 5 qualified |
| `LeaderboardTable.tsx` (342) | Sortable/filterable/paginated table; sort indicator accessible (not color-only); loading/empty/error states; per-row Save-to-shortlist column (Phase 7) |
| `RecencyLine.tsx` (26) | "Data as of {date} · computed {date}" transparency label |
| `DatasetBanner.tsx` (42) | Client banner from `/api/v1/meta`; hidden on production mode and embed pages; "Development dataset." |
| `Header.tsx` (97) / `Footer.tsx` (61) | Site chrome: nav (Leaderboards, positions, methodology, pricing), search combobox, theme toggle; Workspace link when signed in; footer with data-source honesty links |
| `ThemeToggle.tsx` (52) | Light/dark/system toggle |
| `Breadcrumbs.tsx` (23) | Breadcrumb nav helper |
| `LegalDoc.tsx` (55) | Renders legal sections (terms/privacy pages) |

#### `web/app/` — pages and routes

| Route | File | Type / behavior |
| --- | --- | --- |
| `/` | `page.tsx` (130) | Home: hero, feature cards, data-coverage summary, CTA to compare |
| `/compare` | `compare/page.tsx` (60) | SSR shell decoding radar query → `CompareTool`; metadata with OG link |
| `/compare/og-image` | `compare/og-image/route.tsx` | Dynamic OG image: decodes query, fetches payloads, `renderOgCard` |
| `/trend` | `trend/page.tsx` (81) | SSR shell → `TrendTool`; metadata + OG link |
| `/trend/og-image` | `trend/og-image/route.tsx` | Trend OG image |
| `/players/[slug]` | `players/[slug]/page.tsx` (220) | SSR profile: `generateMetadata` (dynamic title/description/OG/JSON-LD), 301 to canonical slug, radar, key stats, sentence, similar, trend card, coverage-gated maps, Add-to-Shortlist |
| `/workspace` | `workspace/page.tsx` (29) + `WorkspaceClient.tsx` (257) | Per-account scouting workspace: shortlist cards with per-status breakdowns, create/remove shortlist, free-cap note, empty/error/signed-out states |
| `/workspace/[id]` | `workspace/[id]/page.tsx` (16) + `ShortlistClient.tsx` (609) | Shortlist detail: status-filter chips, entry table with deliberate status-change control (optional reason → status_history), priority select, tag chips with own-tags autocomplete, notes with relative+absolute timestamps, remove (soft) |
| `/players/[slug]/opengraph-image` | `players/[slug]/opengraph-image.tsx` | Player OG image (real data) |
| `/clubs/[leagueSlug]/[teamSlug]` | `clubs/[...]/page.tsx` (172) | SSR team profile: roster table, squad radar, logo placeholder |
| `/leagues/[leagueCode]` | `leagues/[...]/page.tsx` (6) | Redirects to `/stats` |
| `/leagues/[leagueCode]/stats` | `leagues/[...]/stats/page.tsx` (128) | League per-90 stats table |
| `/leagues/[leagueCode]/index` | `leagues/[...]/index/page.tsx` (62) | League index leaderboard |
| `/leagues/[leagueCode]/positions/[group]` | `leagues/[...]/positions/[group]/page.tsx` (72) | Position-group leaderboard (validates group code) |
| `/positions` | `positions/page.tsx` (71) | Position-group overview with qualifying counts |
| `/methodology` | `methodology/page.tsx` (190) | Generated from registry: inputs, weights (table-wrap), normalization, threshold |
| `/data-coverage` | `data-coverage/page.tsx` (93) | The coverage matrix rendered from the API; honesty notice |
| `/pricing` | `pricing/page.tsx` | Pricing page (Phase 4 stub) |
| `/legal/terms` / `/legal/privacy` | `legal/*/page.tsx` | LegalDoc-rendered drafts |
| `/changelog` | `changelog/page.tsx` | Dated changelog entries (Phase 7 entry added 2026-08-17) |
| `/embed/radar` · `/embed/trend` | `(embed)/embed/*/page.tsx` | Widget pages (bare) |
| 404 | `not-found.tsx` | Honest not-found with search hint |
| `layout.tsx` (48) | Root layout: Sora + IBM Plex Sans via next/font, header, banner, footer |

#### `web/e2e/` — Playwright suite

- **`core.spec.ts`** (113): radar generation (search → add → chart renders), permalink
  reproduces exact state, leaderboard filtering, SSR player profile, axe audit on 4 pages.
- **`breakpoints.spec.ts`** (61): no-horizontal-overflow assertion at 375/768/1440px in
  light + dark themes across 8 core pages.

#### `web/scripts/e2e-server.sh`
- Boots the whole stack for Playwright/LHCI: seeds dev DB, starts FastAPI + `next start`
  (production build), waits for readiness. Windows/cygpath-aware.

#### `web/` config files

- **`next.config.mjs`**: `reactStrictMode`, `output: "standalone"` (small Docker image),
  `env.NEXT_PUBLIC_STATLAS_API_URL` inlined at build time (default
  `http://127.0.0.1:8000`); `STATLAS_API_URL` read at runtime (compose uses
  `http://api:8000`).
- **`tsconfig.json`**: strict, `moduleResolution: "bundler"`, `@/*` path alias,
  `noEmit`.
- **`playwright.config.ts`**: 4 projects (e2e, mobile-375, tablet-768, desktop-1440);
  `webServer` boots via `scripts/e2e-server.sh`; trace retain-on-failure.
- **`lighthouserc.json`**: 3 runs × 2 URLs (player + team profile); assertions: LCP ≤
  2500 ms, CLS ≤ 0.1, performance ≥ 0.85, accessibility = 1, SEO ≥ 0.9,
  best-practices ≥ 0.9 (all error-level); reports to `./lhci-reports`.
- **`package.json`**: deps `next`, `react`, `react-dom`, `lucide-react`; dev deps
  Playwright, axe, lighthouse, @lhci/cli, typescript; **overrides** force
  `@puppeteer/browsers@^3.2.0` and `tmp@^0.2.6` (audit-gate fix — see §14); scripts:
  `dev`, `build`, `start`, `test` (node --test), `test:e2e*`, `perf:audit`.
- **`web/Dockerfile`**: multi-stage (deps → builder → standalone runner), non-root
  `nextjs` user, `ARG NEXT_PUBLIC_STATLAS_API_URL`.
- **`web/styles/tokens.css`** (475 lines): full design-token system — pitch-green brand,
  Okabe-Ito categorical colors, 8-step gray scale, semantic tokens, spacing scale,
  type scale, breakpoints, motion tokens, data font with tabular figures; info/purple
  pipeline-chip tokens (Phase 7).
- **`web/app/globals.css`** (2321 lines): all component styles; `.visually-hidden`
  (screen-reader tables positioned off-screen — closeout fix), `.table-wrap`,
  chip/badge/button/stat-list/leaderboard styles, dataset-banner contrast fix,
  workspace styles (Phase 7): pipeline chips, status-change panel, tag/note controls,
  add-to-shortlist menu.

### 6.12 `docs/` — documentation

> Full index in `docs/README.md`. Headings below name each file's role; all are
> Markdown.

| Area | Files | Role |
| --- | --- | --- |
| Governance | `CONSTITUTION.md` (236) | Master constitution: data-honesty rules, design non-negotiables, never-list, §7 Definition-of-Done checklist (closed by the closeout) |
| Contributing | `CONTRIBUTING.md` (150) | Environment setup, conventions, CI expectations |
| Suite (14-file project docs, merged from the former `project-docs/`) | `suite/PRD.md`, `suite/TechSpec.md`, `suite/AppFlow.md`, `suite/Design.md`, `suite/Schema.md`, `suite/ImplementationPlan.md`, `suite/Tracker.md`, `suite/Rules.md`, `suite/API.md`, `suite/SecurityAndCompliance.md`, `suite/Testing.md`, `suite/Deployment.md`, `suite/Glossary.md`, `suite/RiskRegister.md`, `suite/DOC-SUITE-MAP.md` | The living product/engineering documentation set: requirements, technical spec, screens/states, design system, data model, build plan, status tracker, operating rules, API reference, security/compliance, testing, deployment, glossary, risk register. Supersedes the former `design/`, `product/`, `guides/` docs and the modernization records (`architecture.md`, `folder_structure.md`, `module_dependency.md`, `package_overview.md`, `startup_flow.md`, `analysis_report.md`, `migration_summary.md`, `cleanup-audit-2026-08-13.md`) — removed in the 2026-08-14 docs merge |
| Analytics | `methodology.md` (345) | Statlas Index definition: 16 metrics, weights table, normalization, threshold, public copy |
| | `percentile-rules.md` (107) | Grouping (tier), cadence, §1.4 completeness gate |
| | `data-compliance-notes.md` (132) | Per-source license/ToS/rate-limit review + mitigations |
| | `production-validation-log.md` (119) | Real scrape validation evidence + dataset-mode decision |
| Engineering | `infra-plan.md`, `performance-baseline.md`, `postgres-parity-notes.md`, `timezone-policy.md`, `cleanup-audit-2026-08-14.md` | Unique records: infra/staging plan, LHCI baseline, Postgres parity proof, UTC policy, latest cleanup audit |
| Legal | `terms-of-service-draft.md`, `privacy-policy-draft.md` (both "REQUIRES LAWYER REVIEW"), `founder-legal-checklist.md`, `pre-launch-human-actions.md` | Drafts + tracked human-action checklist |

### 6.13 `data/` and `.github/`

- **`data/coverage_matrix.json`** — generated by the seed from the `data_coverage`
  table; **tracked** (Constitution §3 single source of truth); validated in CI by
  `test_matrix_validation.py`.
- **`.github/workflows/ci.yml`** (199) — 5 jobs: `python` (ruff, pytest, pip-audit),
  `security` (gitleaks), `web` (tsc, node --test, npm audit, production build), `e2e`
  (Playwright suite incl. axe + breakpoints), `lighthouse` (LHCI with LCP < 2.5s
  enforced, reports uploaded as artifacts).
- **`.github/dependabot.yml`** — monthly dependency updates for pip + npm ecosystems.

---

## 7. Data Models & Schemas

All tables are defined in both `app/schema.sql` (PostgreSQL DDL) and `app/models.py`
(ORM). Fields below are **explicit** from both files.

### `leagues`
| Column | Type | Constraints |
| --- | --- | --- |
| id | SERIAL | PK |
| slug | VARCHAR(64) | NOT NULL, UNIQUE |
| name | VARCHAR(128) | NOT NULL |
| country | VARCHAR(64) | NOT NULL |
| tier | league_tier enum | NOT NULL (tier_1/tier_2/tier_3) |
| external_ids | JSONB | NOT NULL default {} |
| updated_at | TIMESTAMPTZ | NOT NULL default now() |

### `teams`
`id` PK · `name` VARCHAR(128) NOT NULL · `league_id` FK→leagues NOT NULL ·
`external_ids` JSONB · `founded_year` INT NULL · `logo_url` TEXT NULL (never
fabricated) · UNIQUE(name, league_id).

### `players`
`id` PK · `canonical_name` VARCHAR(128) NOT NULL · `date_of_birth` DATE NULL ·
`nationality` VARCHAR(64) NULL · `primary_position` VARCHAR(64) NULL (natural-language
label) · `position_group` enum NULL · `external_ids` JSONB · `current_team_id` FK→teams
NULL (free agents) · `created_at` TIMESTAMPTZ. Indexes on canonical_name,
position_group, GIN(external_ids).

### `player_name_aliases`
`id` PK · `player_id` FK→players ON DELETE CASCADE · `source` enum · `source_name_string`
VARCHAR(128) · UNIQUE(player_id, source, source_name_string) · index (source,
source_name_string). Purpose: permanent, auditable spelling store for reconciliation.

### `stat_snapshots` (append-only; versioning key = scrape_date)
`id` PK · `player_id` FK · `team_id` FK NULL · `league_id` FK · `season` VARCHAR(16) ·
`scrape_date` TIMESTAMPTZ · `source` enum · `raw_stats` JSONB (registry-metric-keyed +
`_`-prefixed floor counters) · `minutes_played` FLOAT · `matches_played` INT ·
`status` enum (ingested/flagged/published/failed) · **UNIQUE(player_id, team_id,
league_id, season, source, scrape_date)** — idempotency natural key.

### `percentile_snapshots`
`id` PK · `stat_snapshot_id` FK · `computed_date` TIMESTAMPTZ (the run) ·
`position_group` enum · `league_tier` enum · `metric_name` VARCHAR(64) ·
`percentile_value` FLOAT NULL · `index_score` FLOAT NULL (denormalized onto the
`si_index` row) · `is_published` BOOL default false (the anomaly gate) ·
**UNIQUE(stat_snapshot_id, metric_name, league_tier)** (C1 tier dimension).

### `match_events`
`id` PK · `match_id` VARCHAR(64) · `event_id` VARCHAR(64) · `player_id` FK NULL until
reconciled · `event_type` VARCHAR(64) · `x_coordinate`/`y_coordinate` FLOAT NULL ·
`minute` FLOAT NULL · `outcome` VARCHAR(32) NULL · `source_competition_id` VARCHAR(64) ·
`season` VARCHAR(16) NULL · `extra` JSONB (shot xG, pass end coords, player name) ·
UNIQUE(match_id, event_id).

### `data_coverage`
`id` PK · `league_id` FK NULL (CHECK: non-null OR source='statsbomb') · `source` enum ·
`source_identifier` VARCHAR(128) (league slug or `statsbomb:<comp>:<season>`) ·
`seasons_available` JSONB · `last_successful_scrape` TIMESTAMPTZ · `status` enum
(active/stale/failed) · UNIQUE(source, source_identifier).

### `ingestion_anomalies`
`id` PK · `stat_snapshot_id` FK NULL (NULL = cross-source flag) · `field_name`
VARCHAR(64) · `raw_value` TEXT · `expected_range` TEXT · `flagged_at` TIMESTAMPTZ ·
`resolved` BOOL default false · `resolution_note` TEXT. Index on resolved.

### `reconciliation_queue`
`id` PK · `source` enum · `source_record_key` VARCHAR(128) · `source_name` VARCHAR(128)
· `source_team` VARCHAR(128) NULL · `candidate_player_id` FK NULL · `status` enum
(pending/resolved/ignored) · `confidence` FLOAT NULL · `notes` TEXT · `created_at` ·
`resolved_at` · UNIQUE(source, source_record_key).

### `fixtures`
`id` PK · `league_id` FK · `season` VARCHAR(16) · `api_fixture_id` INT (UNIQUE) ·
`home_team_id`/`away_team_id` FK NULL · `home_team_name`/`away_team_name` VARCHAR(128) ·
`kickoff_utc` TIMESTAMPTZ NULL · `status` VARCHAR(32) NULL · `raw` JSONB.

---

## 8. API Surface

All routes are `GET`, versioned under `/api/v1`, implemented in `app/api/main.py`.
No auth (internal-facing; public tier on Phase 4 roadmap). 400 on `ValueError`; 404 via
`HTTPException`.

| Method & Path | Query params | Purpose | Returns |
| --- | --- | --- | --- |
| GET `/api/v1/health` | — | Liveness + dataset mode | `{status, api_version, dataset_mode}` |
| GET `/api/v1/meta` | — | Metric registry + dataset info | `public_meta()` + dataset mode/note + weekly cadence + index definition |
| GET `/api/v1/leagues` | — | League catalog w/ coverage | `LeagueSummary[]` |
| GET `/api/v1/leagues/{slug}` | — | League detail | teams, coverage, tier, season |
| GET `/api/v1/leagues/{slug}/stats` | `metric` (def si_gls_p90), `season`, `limit` (≤1000) | Per-90 stats table | `LeagueStatsRow[]` |
| GET `/api/v1/leaderboard` | `metric` (si_index), `season`, `league`, `tier`, `position`, `min_minutes`, `page`, `limit` (≤100), `sort_by` (value/minutes/name/club), `sort_dir` | Published leaderboard | `{entries, total, limit, offset, has_more}` |
| GET `/api/v1/players/search` | `q` (req), `limit` (≤25) | Search by name/alias | `SearchResult[]` |
| GET `/api/v1/players/by-slug/{slug}` | — | Full player profile (aggregate) | `PlayerPayload` (404 unknown; 301 signal via `is_canonical`) |
| GET `/api/v1/players/{id}/similar` | `limit` (≤10) | Nearest neighbours | `SimilarPlayer[]` |
| GET `/api/v1/players/{id}/trend` | `metric` (req), `window` (5/10) | Snapshot trend | `TrendPayload` |
| GET `/api/v1/players/{id}/events` | — | Coverage-gated event availability | `{has_coverage, competitions[]}` |
| GET `/api/v1/players/{id}/events/matches` | `competition`, `season` | Matches with events | `EventMatch[]` |
| GET `/api/v1/players/{id}/events/shots` | `match`, `competition`, `season` | Shot events (coverage-gated) | `ShotEvent[]` |
| GET `/api/v1/players/{id}/events/passes` | `match`, `competition`, `season` | Pass events (coverage-gated) | `PassEvent[]` |
| GET `/api/v1/clubs/{league}/{team}` | `season` | Team profile | `TeamPayload` |
| GET `/api/v1/coverage` | `league_id` | Coverage matrix + StatsBomb comps + attribution | `CoveragePayload` |
| GET `/api/v1/positions` | — | Position groups + qualifying counts per tier | `PositionGroupMeta[]` |
| GET `/api/v1/methodology` | — | Metric registry payload | `public_meta()` |

---

## 9. Configuration & Environment Variables

Read by `app/config.py` (backend) / `next.config.mjs` + `lib/api.ts` (web). No dotenv
loader — export in shell/CI. All optional for fixture-demo. *(Explicit — .env.example.)*

| Variable | Default | Purpose | Required |
| --- | --- | --- | --- |
| `DATABASE_URL` | unset → in-memory SQLite | DB connection; `sqlite+pysqlite:///./data/dev.db` for dev server; `postgresql+psycopg2://…` in prod | no |
| `STATLAS_DATASET_MODE` | `fixture-demo` | `production` only after validated scrape | no |
| `STATLAS_DATASET_NOTE` | fixture note | Banner text | no |
| `FBREF_DELAY_SECONDS` | 10.0 | Compliance delay between FBref requests | no |
| `FBREF_JITTER_SECONDS` | 2.0 | Jitter added to FBref delay | no |
| `UNDERSTAT_DELAY_SECONDS` | 5.0 | Understat delay | no |
| `API_FOOTBALL_DELAY_SECONDS` | 2.0 | API-Football delay | no |
| `API_FOOTBALL_DAILY_BUDGET` | 80 | Daily fixture budget (100/day ceiling minus headroom) | no |
| `API_FOOTBALL_KEY` | unset | API-Football key (fixtures layer) | no (fixtures skip) |
| `STATLAS_USER_AGENT` | StatlasAnalytics/0.1 … | Scraper UA string | no |
| `STATLAS_CACHE_DIR` | `.cache` | HTTP cache dir | no |
| `FBREF_ENRICH_POSITIONS` | false | Optional slower position enrichment | no |
| `STATLAS_LOG_LEVEL` | INFO | Log verbosity | no |
| `STATLAS_API_URL` | http://127.0.0.1:8000 | Server-component API URL (runtime) | no |
| `NEXT_PUBLIC_STATLAS_API_URL` | http://127.0.0.1:8000 | Browser API URL (build-time inlined) | no |
| `POSTGRES_USER/PASSWORD/DB` | statlas / statlas_dev_password / statlas | Compose-managed Postgres creds | no |
| `STATLAS_PUBLIC_API_URL` | http://localhost:8000 | Browser-facing API URL baked into web image | no |

---

## 10. Build, Run & Deployment Instructions

### Local dev (fixture data, no keys)

```bash
# 1. Backend deps
pip install -r requirements.txt

# 2. Seed the dev database through the real pipeline
python scripts/seed_dev_db.py

# 3. API on :8000
DATABASE_URL=sqlite+pysqlite:///./data/dev.db \
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# 4. Web on :3000
cd web && npm install && npm run dev
```

### Checks

```bash
python -m pytest -q          # 104 backend tests
python -m ruff check .       # lint (enforced set)
cd web
npx tsc --noEmit             # strict typecheck
npm test                     # 12 pure-module tests
npm run build                # production build
npx playwright test          # 9 e2e tests (boots its own stack)
npm run perf:audit           # Lighthouse CI (needs the stack up)
```

### Docker (production stack)

```bash
docker compose up -d --build --wait              # postgres + api + web on :3000/:8000
docker compose --profile seed run --rm seed      # populate Postgres with fixture-demo data
docker compose down -v                           # full reset (fresh schema on next up)
```

`schema.sql` applies only on a fresh volume (initdb). Overrides via `.env`:
`POSTGRES_*`, `STATLAS_PUBLIC_API_URL`.

### CI/CD (GitHub Actions, `.github/workflows/ci.yml`)

1. **python** — ruff → pytest → pip-audit (fails on vulnerabilities).
2. **security** — gitleaks secret scan (blocks merge on findings).
3. **web** — npm ci → tsc → node --test → npm audit (high fails) → production build.
4. **e2e** — Playwright chromium → full suite (radar, search/filter, axe, breakpoints).
5. **lighthouse** — boots stack, LHCI 3×2 URLs, fails unless LCP < 2.5s / CLS ≤ 0.1 /
   category scores hold; reports uploaded as artifacts.

---

## 11. Data & Control Flow Walkthroughs

### Flow 1 — A weekly refresh run (data → published percentiles)

1. `app/cli.py weekly-refresh --season 2025-26` calls `create_schema()` then
   `run_weekly_refresh(db, season, …)` with real source objects.
2. `ensure_league_catalog` upserts leagues from `config/tiers.json`.
3. For each target league: `fbref_source.fetch_league_stats(slug, season)` →
   `parse_fbref_table` per table → `RawPlayerStatRecord[]` →
   `ingest_source_records` (reconciliation via `Reconciler`, idempotent snapshot
   inserts) → `update_coverage` (fbref row). Tier-1 leagues also run the Understat
   source (xG overlay). Failures are captured per league into `report.errors`.
4. `check_snapshot_bounds` + `cross_source_spot_check` flag anomalies; `blocked_player_ids`
   collects players with unresolved anomalies.
5. `compute_percentiles` groups qualifying snapshots by (league_tier, position_group),
   resolves per-metric values with registry precedence, computes fractional-rank
   percentiles, writes new `percentile_snapshots` rows (unpublished), computes index
   scores. Tier-completeness gate may withhold a tier.
6. `publish_run(computed_date)` flips `is_published=true` — only now are the rows
   queryable.
7. Optional: StatsBomb sync → `link_match_events`; API-Football fixtures → `store_fixtures`.

### Flow 2 — User opens a player profile (SSR → API → DB → UI)

1. Browser GET `/players/erling-haaland` → Next.js server component
   `players/[slug]/page.tsx`.
2. `generateMetadata` fetches the aggregate payload via
   `api.playerBySlug(slug)` → `GET /api/v1/players/by-slug/erling-haaland` →
   `resolve_player_slug` (canonical check; non-canonical → 301) →
   `build_player_payload` (profile + percentiles + raw stats + axes + sentence +
   similar + event coverage in ONE round trip).
3. Page renders header (age computed from DOB vs snapshot date), `KeyStats`,
   `RadarCard` (percentile mode), data-driven sentence, `SimilarPlayers`,
   `TrendCard`, and — only if `has_event_data` — `EventMaps` (coverage-gated).
4. Axes carry `status` so N/A-vs-zero policy renders correctly; recency line shows
   snapshot/computed dates.

### Flow 3 — Comparing two players and sharing

1. `/compare` SSR decodes the radar query (`decodeRadarQuery`); `CompareTool` loads.
2. Search via `SearchCombobox` → `GET /api/v1/players/search` → add up to 4 players;
   URL updates via `encodeRadarQuery` (permalink).
3. `RadarCard` builds chart via `buildRadarPlayers`; percentile/raw toggle.
4. `SharePanel`: copy link (`sharePageUrl`), embed code (`buildEmbedCode`), social
   intents; OG preview is `ogImageUrl` → `/compare/og-image` → real-data SVG →
   `renderOgCard` → 1200×630 PNG.
5. Opening the shared link on another device decodes the same query → same chart state
   (no client storage).

### Flow 4 — Shot map rendering (coverage gate)

1. `player_view.build_player_payload` → `has_player_event_data` (any linked match_event)
   + `get_player_event_coverage` (matrix-confirmed competitions).
2. Player page renders `EventMaps` only when `has_event_data`; otherwise the honest
   "no coverage" note naming covered competitions.
3. `EventMaps` → `/api/v1/players/{id}/events/shots` → `get_player_events` (bounded by
   `_coverage_confirms`) → `ShotMap` plots on the 120×80 pitch with shape+color
   outcomes and StatsBomb attribution.

---

## 12. Dependency Graph Summary

**Internal (module → imports):**

```
api/main.py ──► queries/* ──► models.py, compute/* (percentiles, anomaly_check), config.py
api/player_view.py ──► queries/player_queries, sentences, similar_players, event_queries,
                       compute/percentiles (REGISTRY_FLOOR_KEYS), api/registry_view
api/registry_view.py ──► config.py
cli.py ──► orchestration/weekly_refresh, sources/*, reconciliation, db, models
orchestration/weekly_refresh.py ──► compute/*, reconciliation, models, config
orchestration/event_link.py ──► models, reconciliation (strip_suffixes)
compute/percentiles.py ──► config (registry/tiers), models
compute/index.py ──► compute/percentiles (compute_index_score), models
compute/anomaly_check.py ──► config, models
queries/* ──► models, config, compute/* (player_queries←leaderboard←team/similar)
sources/base.py ──► config
sources/* ──► sources/base, config, (statsbomb: models)
reconciliation.py ──► models
```

**Web internal:** `app/*` → `components/*` + `lib/api.ts`; `components/*` → `lib/*`;
`lib/trend.ts` → `lib/api.ts` + `lib/colors.ts` + `components/TrendChart` types;
`lib/radar.ts` → `lib/colors.ts` + `components/RadarChart` types; `lib/ogRender.tsx` →
`lib/chartSvg.ts`.

**External package purposes** (backend): requests (HTTP), beautifulsoup4 (FBref HTML),
SQLAlchemy (ORM), psycopg2-binary (Postgres driver), fastapi/uvicorn/pydantic (API),
pytest/ruff/pip-audit (quality). (Frontend): next/react/react-dom (framework),
lucide-react (icons), typescript, @playwright/test + @axe-core/playwright (e2e + a11y),
lighthouse + @lhci/cli (perf gate).

---

## 13. Testing Strategy

| Layer | Framework | Count | Notes |
| --- | --- | --- | --- |
| Backend unit/integration | pytest | 104 | In-memory SQLite via ORM models; fixtures for scrapers; no network |
| Frontend pure logic | node --test | 12 | `share.test.ts` (permalink round-trip), `chartSvg.test.ts` (OG image contains real values) |
| E2E | Playwright | 9 | Radar generation, permalink fidelity, leaderboard filtering, SSR profile, axe audit, breakpoint overflow (3 projects × themes) |
| Accessibility | axe-core (in e2e) | — | Fails the suite on any violation on /compare, player, team, leaderboard |
| Performance | Lighthouse CI | 6 runs | LCP < 2.5s etc., enforced in CI |
| Static/lint | ruff + tsc | — | Enforced rule set; strict TS |
| Security | gitleaks, pip-audit, npm audit | — | CI jobs; high severity fails |

Coverage mapping: each `tests/test_*.py` maps to `app/` modules of the same name
(e.g. `test_percentiles.py` → `compute/percentiles.py`; `test_event_queries.py` →
`queries/event_queries.py`). The suite also includes the §3 matrix-validation gate
(`test_matrix_validation.py`) and the C1 regression (`test_tier_completeness.py`).
Full matrix: `docs/suite/Testing.md`.

---

## 14. Known Issues, Technical Debt & Assumptions

**Known limitations / blockers (explicit in docs):**

1. **No real production dataset yet** — `STATLAS_DATASET_MODE=fixture-demo`. FBref
   returns HTTP 403 from the build environment (blocked on a credentialed/proxied run);
   API-Football needs a key. Real Understat + StatsBomb runs were validated
   (production-validation-log.md). The flip to `production` is blocked, not skipped.
2. **Checkout e2e not written** — billing does not exist; Phase 4 must add checkout
   coverage before Pro goes live (Constitution §7 note).
3. **StatsBomb commercial license** — data-compliance-notes.md §3 (re-verified
   2026-08-15) flags the bespoke StatsBomb Public Data User Agreement as
   non-commercial; its §1.2.2 bans commercial exploitation of the data AND any
   analysis derived from it, which conflicts with Pro-gated shot/pass maps —
   resolution required before Phase 4 gates billing on any StatsBomb-backed
   feature (tracked in `pre-launch-human-actions.md` item 3.1).
4. **ToS/Privacy drafts** — flagged REQUIRES LAWYER REVIEW.
5. **Trend granularity** — snapshot-level (weekly scrapes), never per-match; stated in
   the API contract and chart copy.
6. **Competition label nuance** — demo seed labels comp 12 as "Premier League" while the
   live StatsBomb file identifies it as Serie A; coverage gating keys on identifiers,
   not labels (validation log).
7. **Faker city names in synthetic leagues** — non-Premier leagues in the dev DB use
   seeded-RNG fictional player names (honest fixture data).

**Deferred engineering (explicit — migration_summary §7):** BLE001 blind excepts in
`weekly_refresh.py` enrichment are intentional and documented; `native_enum=True` +
`schema.sql` parity verified against Postgres (postgres-parity-notes.md); npm `overrides`
force `@puppeteer/browsers@^3.2.0` + `tmp@^0.2.6` because `@lhci/cli`'s pinned
`lighthouse@12.6.1` chain pulls a vulnerable `extract-zip` (GHSA-jmr9-qjv8-65gv has **no
patched version**) — only `uuid` remains at moderate, under the audit gate.

**Assumptions (inferred):** league external ids in `tiers.json` were transcribed from
public ids and "MUST be verified against live sources at first real scrape" (explicit
note in the file). Player slugs are stable per player-id but not a permanent public
identifier (site-map rules documented).

---

## 15. Security Notes

- **Secrets**: no secrets in source; `.env.example` tracked, `.env*` ignored; gitleaks
  scan in CI blocks on findings; `API_FOOTBALL_KEY` read from env only.
- **Auth**: none on the internal API (public tier is Phase 4). CORS is restricted to
  localhost:3000, GET-only, no credentials.
- **Input validation**: FastAPI query validation (`ge`/`le`/`min_length`/`max_length`,
  whitelists for position/tier/sort); player search query length-capped; `ValueError` →
  400.
- **SSRF/network posture**: scrapers use a declared User-Agent (never a browser spoof),
  rate limiting enforced at runtime, hard abort on 403, bounded retries; StatsBomb hits
  a public static CDN.
- **Supply chain**: pip-audit + npm audit (high fails) + Dependabot + gitleaks in CI.
- **Runtime**: API and web Docker images run as non-root users.
- **Privacy**: no PII collection in the app itself (privacy-policy-draft.md: only
  account/auth + Stripe data planned in Phase 4).

---

## 16. Performance Considerations

- **Caching**: `HttpCache` for scraper HTML (7-day TTL, SHA-256-keyed files);
  `lru_cache` on registry/tier loaders; OG images are cacheable
  (`s-maxage=86400`); permalinks are static URLs so crawlers re-use the image.
- **Query efficiency**: reconciliation preloads players + team names once per batch
  (O(1) lookups); event-link builds name indexes once per run; slug maps are built once
  per payload and shared across lookups (avoids O(N²)); leaderboards sort + paginate
  server-side (never ship thousands of rows).
- **Pagination**: leaderboard `limit`/`offset` + `has_more`; league stats capped at
  `limit` (default 300).
- **Frontend**: SSR pages (fast first paint); charts are SVG with numeric labels; tables
  use `tabular-nums`; fonts self-hosted via next/font (no render-blocking third-party);
  no unoptimized remote images (photos are honest placeholders).
- **Measured**: LHCI baseline LCP 572–740 ms on player/team profiles (~4× under the
  2.5 s budget), CLS ~0, perf/a11y/SEO 1.0 (performance-baseline.md).

---

## 17. Glossary

| Term | Meaning |
| --- | --- |
| Statlas Index | Weighted mean of a player's metric percentiles for their position group (0–100), weights from the registry |
| Tier (1/2/3) | League grouping: Big-5 / mid-tier European / Big-5 second divisions — the percentile cohort dimension |
| Position group | GK/CB/FB/DM/CM/AM/W/ST — percentile and index grouping |
| Qualifying minutes | 900 — minimum minutes for an index score |
| Display floor | Per-metric minimum sample (e.g. 50 pass attempts for pass %) before a value is shown |
| Snapshot | One dated scrape of a player's stats (versioned, immutable) |
| Percentile snapshot | One computation run's percentile/index rows, published-only when the anomaly gate passes |
| Publish gate | `is_published=true` flips only after anomaly checks pass; queries read only published rows |
| Coverage matrix | `data_coverage` table = single source of truth for what data exists |
| Anomaly gate | `ingestion_anomalies`; unresolved anomalies block a player from percentile pools |
| Reconciliation | Mapping source spellings to canonical players via external id → alias → exact name match; never fuzzy |
| Methodology-as-code | Metric registry JSON generated from methodology.md; the site renders from it |
| Fixture-demo | The honest dataset mode until a real scrape validates sources |
| Permalink | URL encoding the exact chart config (`v=1`, players, mode, window) |
| OG image | Open Graph social-preview image generated from real chart data |
| Embed | iframe widget page with unstrippable attribution |
| Progressive pass | Pass advancing ≥10 yards toward goal or into the penalty area (StatsBomb coords) |

---

## 18. Changelog / Version History Summary

Version `0.2.0` (web package). No release tags; phases tracked in
`web/app/changelog/page.tsx`:

- **2026-08-10 — Phase 0**: Constitution v1.1, design system, tokens, methodology,
  percentile rules, compliance notes, legal drafts.
- **2026-08-11 — Phase 1**: schema, sources (FBref/Understat/StatsBomb/API-Football),
  reconciliation, anomaly detection, percentiles + Index, weekly refresh.
- **2026-08-12 — Phase 2**: radar tool, player/team/league profiles, leaderboards,
  compare + permalinks, methodology/coverage/pricing/legal pages, IA docs, dev seed.
- **2026-08-13 — Phase 3**: trends, shot/pass maps, shareable permalinks, dynamic OG
  images, embeddable widgets, event-link step, seed upgrades.
- **2026-08-14 — Closeout**: live Understat/StatsBomb validation + 3 real-drift fixes;
  tier-completeness gate; UTC timezone policy + DTZ lint; Postgres parity
  (native_enum fix); lint/test cleanup; security CI (gitleaks/pip-audit/npm
  audit/Dependabot); Playwright e2e + axe + breakpoint tests; Lighthouse CI with
  LCP < 2.5s; Constitution §7 checklist closed; coverage matrix tracked; README
  polish; `PROJECT_OVERVIEW.md` created.

---

## 19. How to Extend This Project

- **Add a metric**: edit `docs/analytics/methodology.md` → regenerate
  `app/config/metric_registry.json` (must keep unique ids, direction, bounds,
  display_floor, weights summing to 1) → add the FBref/Understat mapping → the
  registry view, methodology page, radar, and matrix-validation tests all pick it up
  automatically (methodology-as-code). Run `tests/test_matrix_validation.py`.
- **Add a data source**: implement `StatsSource` in `app/sources/` returning
  `RawPlayerStatRecord[]`; register delays in `config.py`; wire it into
  `run_weekly_refresh` and the CLI; add fixture-backed tests.
- **Add an API route**: add a query function in `app/queries/`, then a route in
  `app/api/main.py`; the web client adds a method in `web/lib/api.ts` + a type in
  `web/lib/types.ts`.
- **Add a page**: create `web/app/<route>/page.tsx` (SSR) consuming `lib/api.ts`;
  add SEO metadata (title/description/canonical/OG); add the route to the
  breakpoint e2e list.
- **Add a chart**: follow the `RadarChart` pattern — pure geometry, numeric labels,
  colour + shape/dash (never colour alone), data-table alternative, skeleton/empty/
  error states; wire via a `Card` component + share encoding if it should be
  shareable/embeddable.
- **Extend share/embed**: bump `CONFIG_VERSION` in `lib/share.ts`, keep decode
  backward-compatible, extend `buildEmbedCode` + OG route.

---

## 20. Suggested Onboarding Path

1. Read `docs/CONSTITUTION.md` (rules) → `README.md` (surface) → this overview.
2. Read `app/schema.sql` + `app/models.py` (data model).
3. Read `app/orchestration/weekly_refresh.py` (pipeline spine) +
   `app/compute/percentiles.py` (the math + gates).
4. Run `python scripts/seed_dev_db.py` and explore the dev DB with
   `app/cli.py scrape understat --league premier-league --season 2025-26 --dry-run`.
5. Read `app/api/main.py` (API) then `web/lib/api.ts` + `web/lib/types.ts` (contract).
6. Explore one page end-to-end: `web/app/players/[slug]/page.tsx` →
   `app/api/player_view.py` → `app/queries/player_queries.py`.
7. Run the full check set (§10) before making changes; add tests alongside.

---

## 21. Appendix — Files Not Elsewhere Classified

- **`data/`** — contains only the tracked `coverage_matrix.json` (generated); `dev.db`
  is gitignored and built by the seed.
- **`web/package-lock.json`** — npm lockfile (reproducible installs; `npm ci` in CI).
- **`web/playwright-report/`, `web/test-results/`, `web/lhci-reports/`, `.lighthouseci/`**
  — generated test/perf artifacts (gitignored).
- **`LICENSE`** — AGPL-3.0 full text (see §6.1).
- **Emoji headings and badges** — README uses shields.io badges (version, CI, license,
  repo size, last commit, stars, language stack); logo is a documented TODO
  (`<!-- TODO: add assets/logo.svg -->`) — no logo asset exists yet.
- **`docs/engineering/` one-line summaries** — `infra-plan.md` (staging + backup
  strategy), `performance-baseline.md` (LHCI numbers), `postgres-parity-notes.md`
  (native_enum verification), `timezone-policy.md` (UTC everywhere, convert at display),
  `cleanup-audit-2026-08-13.md` (audit found no template artifacts), `migration_summary.md`
  (modernization record + deferred rules), `analysis_report.md` (Phase 1–2 audit).
