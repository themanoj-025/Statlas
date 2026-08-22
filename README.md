<p align="center">
  <img src="assets/logo.svg" width="140" alt="Statlas logo" />
</p>

<h1 align="center">Statlas</h1>

<p align="center">
  <em>Football analytics that shows its work.</em>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Statlas/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Statlas/ci.yml?branch=main&label=CI" alt="CI Status" /></a>
  <a href="https://github.com/themanoj-025/Statlas/releases"><img src="https://img.shields.io/badge/version-0.2.0-144E33" alt="Version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/themanoj-025/Statlas" alt="License: AGPL-3.0" /></a>
  <a href="https://github.com/themanoj-025/Statlas/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Statlas?style=social" alt="Stars" /></a>
  <a href="https://github.com/themanoj-025/Statlas/issues"><img src="https://img.shields.io/github/issues/themanoj-025/Statlas" alt="Issues" /></a>
  <a href="https://github.com/themanoj-025/Statlas/graphs/contributors"><img src="https://img.shields.io/github/contributors/themanoj-025/Statlas" alt="Contributors" /></a>
  <a href="https://github.com/themanoj-025/Statlas/commits/main"><img src="https://img.shields.io/github/last-commit/themanoj-025/Statlas" alt="Last Commit" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs&logoColor=white" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikit-learn&logoColor=white" alt="scikit-learn" />
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome" />
</p>

<p align="center">
  <strong>Statlas</strong> is a football analytics platform that turns per-90 statistics from FBref, Understat, and API-Football — plus StatsBomb event data — into percentile radar comparisons, snapshot trend charts, shot and pass maps, embeddable widgets, and <strong>ML-discovered player archetypes</strong>. Every number carries a dated snapshot, a published methodology, and a traceable data source. No fabricated stats. No black boxes.
</p>

---

## 📑 Table of Contents

- [🖼 Demo](#-demo)
- [✨ Features](#-features)
- [🛠 Tech Stack](#-tech-stack)
- [📋 Prerequisites](#-prerequisites)
- [🚀 Quick Start](#-quick-start)
- [🧭 Usage](#-usage)
- [⚙️ Configuration](#️-configuration)
- [🔌 API](#-api)
- [🗂 Project Structure](#-project-structure)
- [🧪 Testing](#-testing)
- [🐳 Deployment](#-deployment)
- [🗺 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [❓ FAQ \& Troubleshooting](#-faq--troubleshooting)
- [📚 Documentation](#-documentation)
- [📄 License](#-license)
- [🙏 Acknowledgements](#-acknowledgements)
- [⭐ Support](#-support)

---

## 🖼 Demo

> 📸 **Radar comparison** — up to 4 players overlaid, percentile / raw toggle, share panel.

> 📸 **Snapshot trend** — dashed gap segments and transfer markers on the timeline.

> 📸 **Shot map** — StatsBomb events on a proportionally accurate pitch, outcomes by shape and color.

> 📸 **Player archetypes** — ML-discovered player types with typicality scores and distinguishing features.

The seeded dev database makes the full toolset runnable locally in three commands — no API keys required. See [Quick Start](#-quick-start).

---

## ✨ Features

### Core Analytics

- 🧭 **Percentile radar comparisons** — Overlay up to 4 players across 12+ registered metrics. Percentiles computed within position group × league tier, published only from anomaly-checked snapshots.
- 📈 **Snapshot trend charts** — Track players across metrics over rolling windows. Missing history renders as dashed gaps — never interpolated. Transfers annotated from real team changes.
- 🎯 **Shot and pass maps** — StatsBomb event data on an accurate pitch. Progressive passes highlighted, shot outcomes by shape and color, structured data alternative for screen readers.
- 🔗 **Shareable permalinks** — Every radar/trend configuration is a stable URL. Social previews render the actual chart with real data, baked in server-side.
- 🧩 **Embeddable widgets** — Copy an iframe snippet, drop a responsive lazy-loaded chart into any page. Attribution is built-in.

### ML Player Archetypes *(Phase 14)*

- 🤖 **Unsupervised player clustering** — K-means clustering on 12 per-90 statistical features discovers player archetypes: groups of players with similar statistical profiles, separately for each position group.
- 🏷 **Statistically-grounded naming** — Archetypes are named based on their distinguishing features (e.g., "High-Pressing Ball-Winners"), not arbitrary labels. Every archetype has a human-readable description.
- 📊 **Typicality scores** — Each assignment includes a 0–100% typicality measure showing how close a player is to the archetype center. Edge cases flagged as "unusual profiles."
- 🔄 **Governed ML pipeline** — Model cards, versioning, staleness checks, drift detection, rollback plans, and bias audits — all per the ML Constitution Addendum.

### Data Integrity

- 🧱 **Immutable snapshot pipeline** — Append-only, date-versioned data. Corrections are new snapshots, never overwrites.
- 🗺 **Coverage matrix** — Machine-readable source of truth. UI claims are structurally gated on it.
- 🔍 **Anomaly detection** — Values outside plausible bounds are blocked from publication until reviewed.
- 👤 **Player name reconciliation** — Cross-source identity resolution with logged mismatches for manual review.
- 🐊 **Published-only query layer** — The UI is structurally unable to serve unpublished data.

---

## 🛠 Tech Stack

| Layer | Stack |
| --- | --- |
| **Data sources** | FBref, Understat, StatsBomb Open Data, API-Football — throttled, robots.txt-aware, HTTP-cached |
| **Pipeline** | Python 3.10+ (CI runs 3.14), SQLAlchemy 2, BeautifulSoup, requests |
| **ML / ML Ops** | scikit-learn (k-means clustering, StandardScaler, silhouette analysis), joblib (model serialization) |
| **API** | FastAPI, Pydantic, Uvicorn — versioned `/api/v1` |
| **Web** | Next.js 16 (App Router, server-rendered), React 19, TypeScript 5.7, Lucide icons |
| **Database** | PostgreSQL 16 (production) / SQLite (dev & tests) |
| **Ops** | Docker Compose, GitHub Actions CI — 370 pytest tests, ruff lint, Playwright e2e + axe a11y, Lighthouse CI, dependency & secret scanning |

---

## 📋 Prerequisites

- **Python 3.10+** and `pip` — code floor is 3.10; local dev and CI run 3.14
- **Node.js 20+** — Next.js 16 requires ≥ 20.9
- **Docker** *(optional)* — for the [production stack](#-deployment)

---

## 🚀 Quick Start

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

Open **http://localhost:3000**.

> 📝 **Note:** The dataset banner is deliberate. The site labels itself `fixture-demo` until a real scrape validates the sources (`STATLAS_DATASET_MODE=production`). That honesty is a product feature, not a placeholder.

Full build plan: [`docs/suite/ImplementationPlan.md`](docs/suite/ImplementationPlan.md).

---

## 🧭 Usage

### Web Routes

| Route | What it does |
| --- | --- |
| `/compare` | Radar comparison — up to 4 players × metrics, percentile/raw toggle, share panel |
| `/trend` | Snapshot trend — multi-player / multi-metric lines, gap dashes, transfer markers |
| `/players/[slug]` | Player profile — stats, radar, trend card, archetype, coverage-gated maps, similar players |
| `/archetypes` | ML player archetypes — browse all discovered archetypes, player lists, typicality scores |
| `/clubs/[league]/[team]` | Team profile — roster, squad-average radar |
| `/leagues/[league]/stats` | Position-group leaderboards |
| `/positions` | Position-group overview |
| `/data-coverage` | The coverage matrix, rendered from the database |
| `/methodology` | Metric definitions + archetype methodology, generated from the metric registry |
| `/embed/radar` · `/embed/trend` | iframe widget pages (see the share panel for embed code) |

### API Examples

```bash
# Search for a player
curl "http://127.0.0.1:8000/api/v1/players/search?q=haaland&limit=5"

# Get a player's trend data
curl "http://127.0.0.1:8000/api/v1/players/1/trend?metric=si_gls_p90&window=5"

# Get a player's archetype assignment
curl "http://127.0.0.1:8000/api/v1/archetypes/player/1"

# Browse all archetypes
curl "http://127.0.0.1:8000/api/v1/archetypes"

# Get coverage-gated event data
curl "http://127.0.0.1:8000/api/v1/players/1/events"
```

---

## ⚙️ Configuration

All settings are environment variables read by [`app/config.py`](app/config.py). Everything is optional for the fixture-demo run.

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
| `API_FOOTBALL_KEY` | *(unset)* | Optional API-Football key (fixtures layer) |
| `POSTGRES_USER/PASSWORD/DB` | `statlas` defaults | Compose-managed PostgreSQL credentials |

> 💡 **Tip:** The full reference — including per-source scrape delays, jitter, the user-agent string, and the dataset note — is documented in [`.env.example`](.env.example).

---

## 🔌 API

The FastAPI layer serves a versioned `/api/v1` surface. It is the *only* thing the web app talks to — no component touches the database directly. Every response comes from the published-only query layer, so anomaly and publish gates are enforced structurally.

<details>
<summary><strong>📋 Full endpoint reference</strong></summary>

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/meta` | Metric registry, tiers, dataset info |
| `GET` | `/api/v1/leagues` | League catalog |
| `GET` | `/api/v1/leagues/{slug}` | League detail |
| `GET` | `/api/v1/leagues/{slug}/hub` | League hub (emerging players, categories) |
| `GET` | `/api/v1/leagues/{slug}/stats` | League stats table |
| `GET` | `/api/v1/leaderboard` | Filtered leaderboard |
| `GET` | `/api/v1/players/search?q=` | Player search (aliases included) |
| `GET` | `/api/v1/players/by-slug/{slug}` | Full player profile payload |
| `GET` | `/api/v1/players/{id}/similar` | Similar players (cosine similarity) |
| `GET` | `/api/v1/players/{id}/trend` | Snapshot trend data |
| `GET` | `/api/v1/players/{id}/events` | Event coverage |
| `GET` | `/api/v1/players/{id}/events/shots` | Shot events (coverage-gated) |
| `GET` | `/api/v1/players/{id}/events/passes` | Pass events (coverage-gated) |
| `GET` | `/api/v1/clubs/{league}/{team}` | Team profile |
| `GET` | `/api/v1/coverage` | Coverage matrix |
| `GET` | `/api/v1/positions` | Position groups |
| `GET` | `/api/v1/methodology` | Methodology metadata |
| `GET` | `/api/v1/archetypes` | Archetype overview |
| `GET` | `/api/v1/archetypes/{id}` | Archetype detail (players) |
| `GET` | `/api/v1/archetypes/player/{id}` | Player archetype assignment |

</details>

> 📝 **Note:** Current endpoints are internal-facing (the web app's backend). A public, rate-limited API tier is on the [roadmap](#-roadmap).

---

## 🗂 Project Structure

```
Statlas/
├── app/
│   ├── api/                    FastAPI /api/v1 routes
│   ├── compute/                percentiles, Statlas Index, anomaly checks, clustering
│   ├── orchestration/          weekly refresh (scrape → reconcile → compute → publish)
│   ├── queries/                THE data-access layer (published-only reads)
│   ├── sources/                scrapers — FBref, Understat, StatsBomb, API-Football
│   ├── watch/                  watchlist detection and email delivery
│   ├── config.py               env settings, metric registry, league tiers
│   ├── db.py / models/        SQLAlchemy ORM models (domain modules)
│   └── schema.sql              canonical PostgreSQL DDL
├── web/                        Next.js 16 (App Router, server-rendered)
│   ├── app/                    pages — compare, trend, players, archetypes, leagues…
│   ├── components/             RadarChart, TrendChart, ShotMap, PassMap, SharePanel…
│   └── lib/                    api.ts, share.ts, chartSvg.ts (pure SVG for OG images)
├── tests/                      370 pytest tests — unit + integration, in-memory SQLite
├── docs/
│   ├── ml/                     ML governance — model cards, bias audits, monitoring
│   ├── analytics/              methodology, percentile rules, compliance notes
│   ├── engineering/            infra plan, performance baseline, Postgres parity
│   ├── suite/                  14-file project-documentation suite
│   └── legal/                  legal drafts, founder checklist
├── data/
│   └── coverage_matrix.json    machine-readable source of truth
├── scripts/                    seed_dev_db.py, migrations, validation scripts
├── docker-compose.yml          production stack
└── requirements.txt            Python dependencies
```

---

## 🧪 Testing

```bash
# Python — 370 tests, in-memory SQLite, no network
python -m pytest -q

# Frontend — pure module tests
cd web && npm test

# Typecheck
cd web && npx tsc --noEmit

# Production build — verifies every route compiles
cd web && npm run build
```

### Browser Tests

```bash
cd web
npx playwright test            # e2e — radar, search, archetypes, axe audit,
                               # and no-horizontal-overflow at 375/768/1440px
npm run perf:audit             # Lighthouse CI — LCP < 2.5s on player/team profiles
```

### CI Pipeline

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push to `main` and every PR:

| Job | What it runs |
| --- | --- |
| **Python** | `pytest`, `ruff check .`, `pip-audit` |
| **Web** | `npm test`, `npx tsc --noEmit`, `npm run build`, `npm audit` |
| **E2E** | Playwright tests + axe accessibility audit |
| **Lighthouse** | LCP < 2.5s, CLS < 0.1 |
| **Security** | gitleaks secret scan, dependency audit |

No database or API service is required in CI. See [`docs/suite/Testing.md`](docs/suite/Testing.md) for the full test matrix.

---

## 🐳 Deployment

[`docker-compose.yml`](docker-compose.yml) runs the complete production stack — PostgreSQL (with [`app/schema.sql`](app/schema.sql) applied on first boot), the FastAPI layer, and the Next.js standalone server.

```bash
# Start the stack (web on :3000, API on :8000)
docker compose up -d --build --wait

# Populate Postgres with labeled fixture-demo data
docker compose --profile seed run --rm seed
```

> ⚠️ **Warning:** `schema.sql` is applied by the postgres image only on a **fresh volume**. After schema changes, run `docker compose down -v` and up again.

Override via `.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `STATLAS_PUBLIC_API_URL` (your domain in production).

Licensed under [AGPL-3.0](LICENSE) — see [License](#-license).

---

## 🗺 Roadmap

- [x] **Phase 0** — Design system (tokens, type scale, component states, dark mode, colorblind-safe palettes)
- [x] **Phase 1** — Data pipeline (scrapers, versioned snapshots, anomaly gates, coverage matrix, percentiles)
- [x] **Phase 2** — Radar & profiles (comparison tool, player/team/league profiles, leaderboards)
- [x] **Phase 3** — Differentiators (trend charts, shot/pass maps, permalinks, OG images, embeddable widgets)
- [x] **Phase 4** — Monetization (Stripe billing, Pro tier gating, AI assistant, public API)
- [x] **Phase 5** — B2B foundation (API keys, rate limiting, OpenAPI docs)
- [x] **Phase 6** — Similar players (cosine similarity, explainability)
- [x] **Phase 7** — Scouting workspace (shortlists, tags, notes, status pipeline)
- [x] **Phase 8** — Structured search (query builder, saved searches, presets, history)
- [x] **Phase 9** — AI scouting reports (grounded generation, verification gate, exports)
- [x] **Phase 10** — Watchlist & alerts (percentile movement, club change, email delivery)
- [x] **Phase 11** — League hub & emerging players (composite scoring, league pages)
- [x] **Phase 12** — Account system (password reset, email verification, profile settings, account deletion)
- [x] **Phase 13** — Personal dashboard (activity tracking, saved players, recommendations)
- [x] **Phase 14** — ML player archetypes (k-means clustering, archetype discovery, governance)
- [ ] **Phase 15** — Multi-tenant RBAC (org-level permissions, data isolation)
- [ ] **Phase 16** — Advanced analytics (custom dashboards, alert rules, scheduled reports)

---

## 🤝 Contributing

Contributions are welcome. Please read:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — environment setup, code conventions, and the checks CI runs before anything merges
- [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) — the master product constitution: data-honesty rules, design non-negotiables, and the "never do this" list

> 💡 **Tip:** The highest-impact contribution right now is a real, verified scrape run for one source (FBref or Understat) that takes `STATLAS_DATASET_MODE` to `production`.

---

## ❓ FAQ & Troubleshooting

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
<summary><strong>How do player archetypes work?</strong></summary>

Player archetypes are statistically-defined groups of players with similar playing styles, discovered through unsupervised k-means clustering of per-90 statistics. Players are clustered separately by position group (midfielders, strikers, defenders). Each archetype is named based on its distinguishing features and includes a typicality score showing how close a player is to the archetype center. See the [archetypes page](/archetypes) and the [methodology](/methodology#archetypes) for details.

</details>

<details>
<summary><strong>Docker shows a stale schema after I changed <code>schema.sql</code></strong></summary>

The postgres image applies `schema.sql` only on a fresh volume. Run `docker compose down -v` (this deletes the data volume), then `docker compose up -d --build --wait` and re-seed.

</details>

---

## 📚 Documentation

| Area | Link |
| --- | --- |
| Docs index | [`docs/README.md`](docs/README.md) |
| Master constitution | [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md) |
| ML governance | [`docs/ml/`](docs/ml/) — model cards, bias audits, monitoring |
| Analytics | [`docs/analytics/`](docs/analytics/) — methodology, percentile rules, compliance |
| Engineering | [`docs/engineering/`](docs/engineering/) — infra, performance, Postgres parity |
| Legal | [`docs/legal/`](docs/legal/) — legal drafts, founder checklist |
| Project docs suite | [`docs/suite/`](docs/suite/) — 14-file documentation suite ([map](docs/suite/DOC-SUITE-MAP.md)) |

---

## 📄 License

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). If you modify and run this software on a network server, you must make the modified source available to its users — that is the point of the license, and it matches how the project is built.

---

## 🙏 Acknowledgements

- **[FBref](https://fbref.com/)** — primary source for per-90 statistics
- **[Understat](https://understat.com/)** — xG/xA supplements for the Big-5 leagues
- **[StatsBomb Open Data](https://github.com/statsbomb/open-data)** — event-level data behind shot and pass maps; per their terms, any published analysis based on their data must state StatsBomb as the source
- **[API-Football](https://www.api-football.com/)** — fixtures/live-scores layer (free tier)
- **[scikit-learn](https://scikit-learn.org/)** — k-means clustering, preprocessing, evaluation metrics for the ML archetypes system

Every metric's methodology — formula, source precedence, qualification floor — is public in [`docs/analytics/methodology.md`](docs/analytics/methodology.md) and rendered on the site's `/methodology` page.

---

## ⭐ Support

If Statlas is useful to you:

- ⭐ **Star the repository** — it tells us the direction is right
- 🐛 **Report issues** via the [issue tracker](https://github.com/themanoj-025/Statlas/issues)
- 📄 **Read the docs**, run the pipeline, and tell us what breaks
- 🤝 **Contribute** — see [Contributing](#-contributing)

---

<p align="center">
  <strong>Statlas — analytics that shows its work.</strong>
</p>

<p align="center">
  <a href="https://star-history.com/#themanoj-025/Statlas&Date">
    <img src="https://api.star-history.com/svg?repos=themanoj-025/Statlas&type=Date" alt="Star History Chart" width="600" />
  </a>
</p>
