# Statlas Architecture

## System Overview

Statlas is a football (soccer) data visualization and scouting analytics platform built on:
- **Backend:** Python 3.14 + FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** Next.js 15 (React) + TypeScript + Tailwind CSS
- **Data:** FBref, Understat, StatsBomb Open Data, API-Football

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  web/app/        # Pages (SSR + Client Components)           │
│  web/components/ # Reusable UI components                    │
│  web/lib/        # API client, types, utilities              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP API
┌──────────────────────────▼──────────────────────────────────┐
│                      Backend (FastAPI)                        │
│  app/api/         # API routes (thin controllers)            │
│  app/queries/     # Data access layer (SQLAlchemy)           │
│  app/compute/     # Business logic & computations            │
│  app/sources/     # External data source adapters            │
│  app/models.py    # ORM models (single source of truth)      │
│  app/auth.py      # Authentication & session management      │
│  app/config.py    # Settings & environment variables          │
│  app/db.py        # Database session management              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Data Layer                               │
│  PostgreSQL      # Production database                       │
│  SQLite          # Test/development database                 │
│  .cache/         # HTTP response cache for scrapers          │
└─────────────────────────────────────────────────────────────┘
```

## Backend Structure (`app/`)

### Entry Points
- `app/api/main.py` — FastAPI application (ASGI entry point)
- `app/cli.py` — CLI commands (for manual operations)
- `uvicorn app.api.main:app` — Production server

### Core Modules

| Module | Responsibility | Key Functions |
|--------|---------------|---------------|
| `config.py` | Settings, env vars, config loading | `get_settings()`, `load_registry()`, `plan_limits()` |
| `db.py` | Database session management | `session_scope()` context manager |
| `auth.py` | Password hashing, sessions, tokens | `hash_password()`, `create_session()`, `user_from_session()` |
| `models.py` | All ORM models (30+ classes) | Single source of truth for schema |
| `schema.sql` | PostgreSQL DDL | Canonical schema definition |

### API Layer (`app/api/`)

Thin controllers that map HTTP → domain logic:

| Route Module | Responsibility |
|-------------|---------------|
| `main.py` | App factory, router registration, middleware |
| `deps.py` | Shared dependencies (`require_user`) |
| `billing_views.py` | Auth (register/login/logout), Stripe billing |
| `workspace_views.py` | Shortlists, entries, notes, tags |
| `search_views.py` | Structured search, presets, saved searches |
| `report_views.py` | AI scouting reports, exports |
| `watch_views.py` | Watchlist, alerts, notification preferences |
| `dashboard_views.py` | Personal dashboard widgets |
| `org_views.py` | Organizations, membership, RBAC |
| `transfer_views.py` | Transfer intelligence, market data |
| `tactical_views.py` | Passing networks, heatmaps, formations |
| `public_views.py` | Public API (API key auth, rate limiting) |
| `assistant_views.py` | AI assistant chat |
| `player_view.py` | Player profile endpoints |
| `registry_view.py` | Methodology/registry metadata |

### Query Layer (`app/queries/`)

Data access functions that enforce business rules:

| Query Module | Responsibility |
|-------------|---------------|
| `player_queries.py` | Player profiles, percentiles, search |
| `leaderboard_queries.py` | Leaderboard filtering, pagination |
| `team_queries.py` | Team profiles |
| `league_queries.py` | League catalog, stats |
| `event_queries.py` | Shot/pass maps (coverage-gated) |
| `trend_queries.py` | Time-series trends |
| `similar_players.py` | Explainable similarity |
| `structured_search.py` | Multi-condition query execution |
| `workspace_queries.py` | Shortlist CRUD (ownership-enforced) |
| `watch_queries.py` | Watch/alert management |
| `dashboard_queries.py` | Dashboard aggregation |
| `org_queries.py` | RBAC, membership, audit |
| `transfer_queries.py` | Transfer candidates, valuations |
| `market_queries.py` | Market data, value proxies |
| `coverage_queries.py` | Data coverage matrix |

### Compute Layer (`app/compute/`)

Pure computation modules (no DB dependencies):

| Compute Module | Responsibility |
|---------------|---------------|
| `percentiles.py` | Fractional-rank percentile computation |
| `index.py` | Statlas Index (weighted metric average) |
| `anomaly_check.py` | Data quality anomaly detection |
| `clustering.py` | ML player archetypes (KMeans) |
| `emerging.py` | Emerging player score computation |
| `opportunity.py` | Hidden gems, position scarcity |
| `risk.py` | Transfer risk assessment |
| `formation.py` | Formation detection from events |
| `passing_network.py` | Network graph analysis |
| `spatial_analysis.py` | Zone heatmaps, pressure maps |
| `market_validation.py` | Market data validation rules |

### Data Sources (`app/sources/`)

External data adapters implementing `StatsSource` interface:

| Source Module | Data Provider | Coverage |
|--------------|---------------|----------|
| `fbref.py` | FBref (Sports Reference) | Per-90 stats, Big-5 leagues |
| `understat.py` | Understat | xG/xA, top 5 European leagues |
| `statsbomb.py` | StatsBomb Open Data | Event-level (specific competitions) |
| `api_football.py` | API-Football | Fixtures, live scores |
| `market_data.py` | Fixture market data | Valuations (test mode) |
| `base.py` | Shared infrastructure | Rate limiting, caching, retry |

### Orchestration (`app/orchestration/`)

Pipeline automation:

| Module | Responsibility |
|--------|---------------|
| `weekly_refresh.py` | Weekly data refresh pipeline |
| `event_link.py` | Event-to-player reconciliation |

### Notifications (`app/notifications/`)

| Module | Responsibility |
|--------|---------------|
| `email.py` | Resend email delivery |

### Watch Detection (`app/watch/`)

| Module | Responsibility |
|--------|---------------|
| `detection.py` | Alert trigger detection |
| `delivery.py` | Alert delivery (email, in-app) |

## Frontend Structure (`web/`)

### Pages (`web/app/`)

Next.js App Router pages (SSR where needed for SEO):

| Route | Page | SSR? |
|-------|------|------|
| `/` | Home | Yes |
| `/positions` | Leaderboards | Yes |
| `/players/[slug]` | Player profile | Yes |
| `/clubs/[league]/[team]` | Team profile | Yes |
| `/compare` | Compare tool | No |
| `/trend` | Trend analysis | No |
| `/search` | Structured search | No |
| `/archetypes` | ML archetypes | No |
| `/transfers` | Transfer intelligence | No |
| `/tactical` | Tactical analysis | No |
| `/workspace` | Scouting workspace | No |
| `/reports` | AI reports | No |
| `/watchlist` | Watchlist & alerts | No |
| `/dashboard` | Personal dashboard | No |
| `/orgs` | Organizations | No |
| `/account` | Account settings | No |
| `/pricing` | Pricing page | Yes |
| `/methodology` | Methodology | Yes |
| `/data-coverage` | Coverage matrix | Yes |

### Components (`web/components/`)

35 reusable React components:

| Component | Purpose |
|-----------|---------|
| `RadarChart.tsx` | SVG radar visualization |
| `TrendChart.tsx` | Time-series trend chart |
| `LeaderboardTable.tsx` | Sortable/filterable table |
| `SearchCombobox.tsx` | Player search autocomplete |
| `CompareTool.tsx` | Multi-player comparison |
| `Header.tsx` | Navigation + auth |
| `Footer.tsx` | Site footer |
| `EventMaps.tsx` | Shot/pass map visualizations |
| `SimilarPlayers.tsx` | Explainable similarity display |
| `PlayerTransferSection.tsx` | Transfer intelligence panel |
| `PlayerArchetypeSection.tsx` | Archetype display |

### Library (`web/lib/`)

| Module | Purpose |
|--------|---------|
| `api.ts` | API client functions |
| `types.ts` | TypeScript type definitions |
| `chartSvg.ts` | SVG chart rendering |
| `radar.ts` | Radar chart data processing |
| `format.ts` | Number/date formatting |
| `colors.ts` | Design token colors |
| `share.ts` | URL state management |

## Data Flow

### Ingestion Pipeline
```
External Sources → Scraper Modules → Validation → Reconciliation → DB (stat_snapshots)
                                                                         ↓
                                                              Percentile Computation
                                                                         ↓
                                                              Index Calculation
                                                                         ↓
                                                              Anomaly Check
                                                                         ↓
                                                              Publish (is_published=true)
```

### Query Flow
```
API Request → Route Handler → Query Function → SQLAlchemy ORM → DB → Response
                                    ↓
                            Ownership Check
                                    ↓
                            Tier/Season Filter
                                    ↓
                            Published Only Gate
```

## Key Design Patterns

### 1. Coverage Gating
Every feature that depends on external data checks `data_coverage` before rendering. Never implies coverage that doesn't exist.

### 2. Ownership Enforcement
Every read/write on user-owned resources verifies the logged-in user owns or has access to that resource. 404 on foreign/missing IDs (never 403 that leaks existence).

### 3. Append-Only Versioning
All time-series data is append-only, versioned by scrape date. Historical data is never mutated.

### 4. Anomaly Gate
Data quality anomalies block publication until resolved. Flagged values are never silently published.

### 5. Single Access Gate
`has_pro_access()` is THE single function for Pro feature gating. Reads from subscriptions table, never scattered flags.

## Configuration

### Environment Variables
All configuration via environment variables (see `.env.example`):
- `DATABASE_URL` — Database connection string
- `STATLAS_DATASET_MODE` — fixture-demo | production
- `STRIPE_SECRET_KEY` — Stripe billing (optional)
- `ANTHROPIC_API_KEY` — AI assistant (optional)
- `RESEND_API_KEY` — Email delivery (optional)

### Config Files (`app/config/`)
- `metric_registry.json` — Metric definitions, weights, formulas
- `tiers.json` — League tier assignments
- `pricing.json` — Subscription plan limits
- `search_presets.json` — Curated search templates

## Testing

### Test Structure
```
tests/
├── conftest.py           # Shared fixtures (in-memory SQLite)
├── test_*.py             # Unit + integration tests (478 total)
└── fixtures/             # Test data files
```

### Test Patterns
- In-memory SQLite for speed
- Fixture data for deterministic tests
- Real function calls (not mocked)
- 100% of previously-passing tests must pass after any change

## Security

### Authentication
- PBKDF2-HMAC-SHA256 password hashing (600K iterations)
- Session tokens hashed before storage (SHA-256)
- Login rate limiting (5 failures/10min → 15min lockout)

### Authorization
- `require_user()` dependency for authenticated routes
- `user_has_permission()` for RBAC (org contexts)
- Ownership checks on every resource access

### Data Protection
- No card data stored (Stripe hosted checkout)
- `.env` in `.gitignore`
- All secrets via environment variables

## Deployment

### Docker
- `Dockerfile` — Python backend
- `docker-compose.yml` — Full stack (backend + frontend + PostgreSQL)

### CI/CD
- `.github/workflows/ci.yml` — Tests, lint, typecheck
- `.github/workflows/codeql.yml` — Security scanning
- `.github/workflows/gitleaks.yml` — Secret scanning

## Performance

### Backend
- SQLAlchemy query optimization (eager loading, pagination)
- Redis caching for computed queries (planned)
- Idempotent ingestion (re-runs don't duplicate)

### Frontend
- SSR for SEO-critical pages (player profiles, leaderboards)
- Client-side rendering for interactive tools
- Lighthouse CI enforces LCP < 2.5s

## Monitoring

### Observability
- Structured logging (Python logging module)
- Anomaly detection on data pipeline
- Webhook event logging (Stripe)

### Error Tracking
- 500 errors logged with context
- Stack traces in server logs only (never to clients)
