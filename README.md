<p align="center">
  <!-- TODO: add assets/logo.svg — inline wordmark, pitch-green on transparent -->
  <img src="https://img.shields.io/badge/version-0.2.0-144E33" alt="Version 0.2.0" />
  <img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Statlas/ci.yml?branch=main" alt="CI status" />
  <img src="https://img.shields.io/github/license/themanoj-025/Statlas" alt="License: AGPL-3.0" />
  <img src="https://img.shields.io/github/stars/themanoj-025/Statlas?style=social" alt="Stars" />
  <img src="https://img.shields.io/github/repo-size/themanoj-025/Statlas" alt="Repository size" />
  <img src="https://img.shields.io/github/last-commit/themanoj-025/Statlas" alt="Last commit" />
</p>

<h1 align="center">Statlas</h1>

<p align="center">
  <em>Football analytics that shows its work.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs&logoColor=white" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome" />
</p>

**Statlas** is a football analytics platform for scouts, analysts, agents, media, and serious fans. It turns per-90 statistics from FBref, Understat and API-Football — plus StatsBomb event data — into percentile radar comparisons, snapshot trend charts, shot and pass maps, and embeddable widgets. Every number carries a dated snapshot and a published methodology: coverage is gated by a machine-readable matrix, missing history is drawn as gaps, and nothing is ever presented as data that isn't.

---

## 📑 Table of contents

- [🖼 Demo](#-demo)
- [✨ Features](#-features)
- [🛠 Tech stack](#-tech-stack)
- [📋 Prerequisites](#-prerequisites)
- [🚀 Quick start](#-quick-start)
- [🧭 Usage](#-usage)
- [⚙️ Configuration](#️-configuration)
- [🔌 API](#-api)
- [🗂 Project structure](#-project-structure)
- [🧪 Testing](#-testing)
- [🐳 Deployment](#-deployment)
- [🗺 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [❓ FAQ & troubleshooting](#-faq--troubleshooting)
- [📚 Documentation](#-documentation)
- [📄 License](#-license)
- [🙏 Acknowledgements](#-acknowledgements)
- [⭐ Support](#-support)

---

## 🖼 Demo

> 📸 **Screenshot:** radar comparison — four players overlaid, percentile / raw toggle.
>
> 📸 **Screenshot:** snapshot trend — dashed gap segment and transfer marker visible on the timeline.
>
> 📸 **Screenshot:** shot map — StatsBomb events on a proportionally accurate pitch, outcomes by shape and color.

The seeded dev database makes the full toolset runnable locally in three commands — no API keys required ([Quick start](#-quick-start)).

---

## ✨ Features

- 🧭 **Percentile radar comparisons** — Overlay up to 4 players across 16 registered metrics (goals, xG, progressive passes, pressures, and more) and toggle between percentile rank and raw per-90 values. Percentiles are computed against position-group × league-tier peers and only published from qualified, anomaly-checked snapshots.
- 📈 **Snapshot trend charts** — Follow up to 3 players across one or more metrics over rolling 5- or 10-snapshot windows. Missing history (injury, scrape failure) renders as a dashed gap, never a falsely smooth line, and transfers are annotated from real team changes between snapshots.
- 🎯 **Shot and pass maps** — StatsBomb event data plotted on an accurate pitch, with shot outcomes distinguished by shape *and* color, progressive passes highlighted, and a structured data-table alternative for screen readers. Entry points render only where the coverage matrix confirms the data exists.
- 🔗 **Shareable permalinks** — Every radar and trend configuration is a stable URL; opening the link reproduces the exact chart state with no prior client state. The social preview renders the actual chart with actual data baked in server-side — not a site-wide banner.
- 🧩 **Embeddable widgets** — Copy an iframe snippet from any share panel and drop a responsive, lazy-loaded radar or trend chart into your own page. The "Powered by Statlas" attribution is part of the widget and cannot be stripped.
- 🧱 **A data-integrity backbone** — Immutable, dated snapshots (append-only, never overwritten), player-name reconciliation across sources, anomaly gates that block questionable values from publication, and a published-only query layer the UI is structurally unable to bypass.
- 🗺 **A coverage matrix, not claims** — `data_coverage` is the single source of truth for what data exists. The UI, the `/data-coverage` page, and the tests all read from it; a screen cannot claim coverage the matrix doesn't contain.
- 🐳 **One-command production stack** — Docker Compose boots PostgreSQL, the FastAPI layer, and the Next.js standalone server. The site labels itself `fixture-demo` until a real scrape run validates the sources — on purpose.

---

## 🛠 Tech stack

| Layer | Stack |
| --- | --- |
| Data sources | FBref, Understat, StatsBomb Open Data, API-Football — throttled, robots.txt-aware, HTTP-cached |
| Pipeline | Python 3.10+ (CI runs 3.14), SQLAlchemy 2, BeautifulSoup, requests |
| API | FastAPI, Pydantic, Uvicorn — versioned `/api/v1` |
| Web | Next.js 16 (App Router, server-rendered), React 19, TypeScript 5.7, Lucide icons |
| Database | PostgreSQL (production) / SQLite (dev and tests) |
| Ops | Docker Compose, GitHub Actions CI — pytest + ruff, typecheck, production build, Playwright e2e + axe, Lighthouse CI, dependency & secret scanning |

---

## 📋 Prerequisites

- **Python 3.10+** and `pip` (`pip install -r requirements.txt`) — the code floor is 3.10; local dev and CI run 3.14
- **Node.js 20+** (for the web app; Next.js 16 requires ≥ 20.9)
- Optional: **Docker** for the [production stack](#-deployment)

---

## 🚀 Quick start

The dev workflow runs the real pipeline against labeled fixtures plus deterministic synthetic leagues — no API keys, no network.

```bash
# 1. Seed the dev database through the REAL pipeline
python scripts/seed_dev_db.py

# 2. Start the API layer (serves /api/v1 on :8000)
DATABASE_URL=sqlite+pysqlite:///./data/dev.db \
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# 3. Start the web app (Next.js on :3000)
cd web && npm install && npm run dev
```

Open http://localhost:3000.

> 📝 **Note:** the dataset banner is deliberate. The site labels itself `fixture-demo` until a real scrape validates the sources (`STATLAS_DATASET_MODE=production` — see [Configuration](#️-configuration)). That honesty is a product feature, not a placeholder.

Full build plan and run guide: [`docs/suite/ImplementationPlan.md`](docs/suite/ImplementationPlan.md).

---

## 🧭 Usage

The main tools:

| Route | What it does |
| --- | --- |
| `/compare` | Radar comparison — up to 4 players × metrics, percentile/raw toggle, share panel |
| `/trend` | Snapshot trend — multi-player / multi-metric lines, gap dashes, transfer markers |
| `/players/[slug]` | Player profile — stats, radar, trend card, coverage-gated maps, similar players |
| `/clubs/[league]/[team]` | Team profile — roster, squad-average radar |
| `/leagues/[league]/stats` | Position-group leaderboards |
| `/positions` | Position-group overview |
| `/data-coverage` | The coverage matrix, rendered from the database |
| `/methodology` | Metric definitions, generated from the metric registry |
| `/embed/radar` · `/embed/trend` | iframe widget pages (see the share panel for embed code) |
| `/compare/og-image` · `/trend/og-image` | Dynamic OG image generators (real data, real chart) |

The API is browsable directly:

```bash
curl "http://127.0.0.1:8000/api/v1/players/search?q=haaland&limit=5"
curl "http://127.0.0.1:8000/api/v1/players/1/trend?metric=si_gls_p90&window=5"
curl "http://127.0.0.1:8000/api/v1/players/1/events"          # coverage-gated shot/pass data
```

---

## ⚙️ Configuration

All settings are environment variables read by [`config.py`](config.py) — there is no dotenv loader, so export them in your shell/CI or set them on the run command. Everything is optional for the fixture-demo run.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+pysqlite:///./data/dev.db` | Database connection (PostgreSQL DSN in production) |
| `STATLAS_DATASET_MODE` | `fixture-demo` | Set to `production` only after a real scrape validates the sources |
| `STATLAS_API_URL` | `http://127.0.0.1:8000` | API base URL used by server components |
| `NEXT_PUBLIC_STATLAS_API_URL` | `http://127.0.0.1:8000` | API base URL used by browser components |
| `STATLAS_LOG_LEVEL` | `INFO` | Pipeline log verbosity |
| `STATLAS_CACHE_DIR` | `.cache` | HTTP cache directory for scrapers |
| `FBREF_DELAY_SECONDS` | `10.0` | Compliance-floor delay between FBref requests |
| `API_FOOTBALL_DAILY_BUDGET` | `80` | Daily request budget for the API-Football free tier |
| `API_FOOTBALL_KEY` | unset | Optional API-Football key (fixtures layer) |
| `POSTGRES_USER/PASSWORD/DB` | statlas defaults | Compose-managed PostgreSQL credentials |

> 💡 **Tip:** the full reference — including per-source scrape delays, jitter, the user-agent string, and the dataset note — is documented in [`.env.example`](.env.example).

---

## 🔌 API

The FastAPI layer serves a versioned `/api/v1` surface, and it is the *only* thing the web app talks to — no component touches the database directly. Every response comes from the published-only query layer, so the anomaly and publish gates are enforced structurally rather than by convention.

> 📝 **Note:** the current endpoints are internal-facing (the web app's backend). A public, rate-limited API tier is on the [Phase 4 roadmap](#-roadmap).

---

## 🗂 Project structure

```
Statlas/
├── cli.py / api/main.py           pipeline CLI + FastAPI /api/v1 entry points
├── sources/                       scrapers — FBref, Understat, StatsBomb, API-Football
├── orchestration/                 weekly refresh (scrape → reconcile → compute → publish),
│                                  player-name linking for match events (event_link.py)
├── compute/                       percentiles, Statlas Index, anomaly checks
├── reconciliation.py              player identity resolution
├── queries/                       THE data-access layer (trend, event, coverage queries)
├── api/                           thin FastAPI wrapper over queries/
├── config.py + config/            env settings, metric registry, league tiers
├── db.py / models.py / schema.sql SQLite dev / PostgreSQL production DDL
├── scripts/seed_dev_db.py         rebuilds data/dev.db through the real pipeline
├── web/                           Next.js 16 app
│   ├── app/compare, app/trend     shareable tools (URL-state driven)
│   ├── app/(embed)/embed/*        iframe widget pages
│   ├── app/*/og-image             dynamic OG image route handlers
│   ├── components/                RadarChart, TrendChart, ShotMap, PassMap, SharePanel…
│   └── lib/                       api.ts, share.ts, chartSvg.ts (pure SVG for OG images)
├── tests/                         104 tests — unit + integration, no network
└── docs/                          constitution, methodology, legal drafts, and the
                                   project-documentation suite (suite/)
```

---

## 🧪 Testing

```bash
python -m pytest -q     # 104 tests — unit + integration, in-memory SQLite, no network
cd web
npm test                # 12 tests for the pure share / SVG modules (node --test)
npx tsc --noEmit        # strict typecheck
npm run build           # production build — verifies every route compiles
```

The web app also has a full browser suite:

```bash
cd web
npx playwright test     # 9 e2e tests — radar generation, search/filter, axe audit,
                        # and no-horizontal-overflow at 375/768/1440px in both themes
npm run perf:audit      # Lighthouse CI — enforces LCP < 2.5s on player/team profiles
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs all of the above on every push to `main` and on every pull request, plus `ruff check .` on the Python side, `npm audit` + `pip-audit` dependency scanning, and a gitleaks secret scan. The same checks run locally with the commands above; no database or API service is required in CI.

See [`docs/suite/Testing.md`](docs/suite/Testing.md) for the full test matrix.

---

## 🐳 Deployment

[`docker-compose.yml`](docker-compose.yml) runs the complete production stack — PostgreSQL (with [`schema.sql`](schema.sql) applied on first boot), the FastAPI layer, and the Next.js standalone server.

```bash
docker compose up -d --build --wait              # stack on :3000 (web) and :8000 (api)
docker compose --profile seed run --rm seed      # populate Postgres with the labeled
                                                 # fixture-demo data
```

- Open http://localhost:3000. The dataset banner stays honest (`fixture-demo`) until a real scrape validates the sources.
- `schema.sql` is applied by the postgres image only on a **fresh volume**; after schema changes run `docker compose down -v` and up again.
- Override via `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `STATLAS_PUBLIC_API_URL` (the browser-facing API URL baked into the web image — your domain in production).
- Licensed under [AGPL-3.0](LICENSE) — see [License](#-license).

---

## 🗺 Roadmap

- [x] **Phase 0 — Design system** — tokens, type scale, component-state spec, dark mode and colorblind-safe palettes
- [x] **Phase 1 — Data pipeline** — scrapers, versioned snapshots, anomaly gates, coverage matrix, percentile computation
- [x] **Phase 2 — Radar & profiles** — site map, comparison tool, player/team/league profiles, leaderboards
- [x] **Phase 3 — Differentiators** — trend charts, shot/pass maps, shareable permalinks, dynamic OG images, embeddable widgets
- [ ] **Phase 4 — Monetization & polish** — Pro tier gating (full league access, unlimited trends, maps), AI assistant, public API, final accessibility/performance pass
- [ ] **Phase 5 — B2B** — licensed data feeds (Wyscout / Opta / Sportmonks), API tier for clubs and agents

---

## 🤝 Contributing

Contributions are welcome. Please read:

- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — environment setup, code conventions, and the checks CI runs before anything merges
- [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) — the master product constitution: data-honesty rules, design non-negotiables, and the "never do this" list

> 💡 **Tip:** the highest-impact contribution right now is a real, verified scrape run for one source (FBref or Understat) that takes `STATLAS_DATASET_MODE` to `production`.

---

## ❓ FAQ & troubleshooting

<details>
<summary><strong>Why do shot/pass maps appear for only some players?</strong></summary>

StatsBomb Open Data covers specific competitions, not all of them. The coverage matrix gates the feature: the entry point only renders where event data exists, and player pages state exactly which competitions have event data. This is deliberate — claiming coverage the product doesn't have would violate the Constitution.

</details>

<details>
<summary><strong>Why does the trend chart draw dashed segments?</strong></summary>

Each point is one dated snapshot from the versioned `stat_snapshots` table. If a snapshot is missing (injury period, scrape failure logged in `ingestion_anomalies`), the line breaks and continues dashed rather than interpolating through data that doesn't exist. A smooth line through missing data would be misleading.

</details>

<details>
<summary><strong>What does the "fixture-demo" banner mean?</strong></summary>

The site labels its dataset mode honestly. Until a real pipeline run validates the sources against live pages, the UI shows a banner instead of pretending the numbers are production data. Flip `STATLAS_DATASET_MODE=production` only after that validation.

</details>

<details>
<summary><strong>Can I embed a chart in my own article or site?</strong></summary>

Yes. Open any radar or trend configuration, open the share panel, and copy the embed code — a responsive, lazy-loaded iframe with attribution built in. See `/embed/radar` and `/embed/trend` for the widget pages.

</details>

<details>
<summary><strong>Docker shows a stale schema after I changed <code>schema.sql</code></strong></summary>

The postgres image applies `schema.sql` only on a fresh volume. Run `docker compose down -v` (this deletes the data volume), then `docker compose up -d --build --wait` and re-seed.

</details>

---

## 📚 Documentation

- [`docs/README.md`](docs/README.md) — full docs index, organized by area
- [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) — the master product constitution
- [`docs/suite/`](docs/suite/) — the 14-file project-documentation suite (PRD, TechSpec, AppFlow, Design, Schema, ImplementationPlan, Tracker, Rules, API, SecurityAndCompliance, Testing, Deployment, Glossary, RiskRegister; start at [`DOC-SUITE-MAP.md`](docs/suite/DOC-SUITE-MAP.md)); runtime tokens in `web/styles/tokens.css`
- [`docs/analytics/`](docs/analytics/) — data rules and methodology (`methodology.md`, `percentile-rules.md`, `data-compliance-notes.md`, `production-validation-log.md`)
- [`docs/engineering/`](docs/engineering/) — engineering records (infra plan, performance baseline, Postgres parity, timezone policy, cleanup audits)
- [`docs/legal/`](docs/legal/) — legal drafts and founder checklist

---

## 📄 License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). If you modify and run this software on a network server, you must make the modified source available to its users — that is the point of the license, and it matches how the project is built.

---

## 🙏 Acknowledgements

- **FBref** — primary source for per-90 statistics
- **Understat** — xG/xA supplements for the Big-5 leagues
- **StatsBomb Open Data** — event-level data behind the shot and pass maps; per their terms, any published analysis based on their data must state StatsBomb as the source
- **API-Football** — fixtures/live-scores layer (free tier)

The methodology for every metric — formula, source precedence, qualification floor — is public in [`docs/analytics/methodology.md`](docs/analytics/methodology.md) and rendered on the site's `/methodology` page.

---

## ⭐ Support

If Statlas is useful to you:

- ⭐ Star the repository — it tells us the direction is right
- 🐛 Report issues via the [issue tracker](https://github.com/themanoj-025/Statlas/issues)
- 📄 Read the docs, run the pipeline, and tell us what breaks

> **Statlas — analytics that shows its work.**
