# Repository Restructuring — Discovery Report

## Current Structure Overview

```
app/                          # Python backend (FastAPI)
├── __init__.py
├── activity.py               # Activity logging
├── api_keys.py               # API key management
├── assistant.py              # AI assistant
├── auth.py                   # Authentication (PBKDF2, sessions)
├── billing.py                # Stripe billing
├── cli.py                    # CLI entry point
├── config.py                 # Settings + env loading
├── db.py                     # Database session
├── models.py                 # ALL ORM models (1615 lines — monolithic)
├── reconciliation.py         # Name reconciliation
├── report_export.py          # Report export
├── reports.py                # Report generation
├── schema.sql                # DDL
├── api/                      # API routes (17 view files)
│   ├── main.py               # App factory + router registration
│   ├── deps.py               # require_user dependency
│   └── *_views.py            # 15 view modules
├── compute/                  # Computation (11 modules)
├── config/                   # JSON config files
├── notifications/            # Email (1 file)
├── orchestration/            # Weekly refresh
├── queries/                  # Data access (20 modules)
├── sources/                  # External data sources (6 modules)
└── watch/                    # Watchlist detection
```

**Scale:** 76 Python files, 18 API views, 20 query modules, 12 compute modules, 35 test files.

## Key Findings

### 1. `models.py` is Monolithic (HIGH RISK)
- 1615 lines, 30+ ORM models in a single file
- Imported by 51 other modules across the codebase
- Splitting requires backward-compatible re-exports in `models.py`

### 2. API Routes are Flat (MEDIUM RISK)
- 17 view files at the same level under `app/api/`
- `main.py` registers all 17 routers
- Moving to `app/api/routes/` requires updating router imports in `main.py`

### 3. Queries are Flat (LOW RISK)
- 20 query modules at the same level
- Well-named, clear responsibilities
- Could be organized by domain but low ROI

### 4. No Circular Imports Found
- Import graph is clean and hierarchical
- `models` is the most-imported module (51 imports)
- `config` is second (42 imports)

### 5. Entry Points
- `app/api/main.py` — FastAPI app (ASGI)
- `app/cli.py` — CLI commands
- `uvicorn app.api.main:app` — production server

### 6. Framework Coupling
- FastAPI routers in all `*_views.py` files
- SQLAlchemy ORM in `models.py`
- Next.js pages in `web/app/`

## Risk Assessment

| Item | Risk | Blast Radius | Mitigation |
|------|------|-------------|------------|
| Split models.py | HIGH | 51 modules | Backward-compatible re-exports |
| Move API routes | MEDIUM | 17 views + main.py | Keep old imports working |
| Move queries | LOW | 20 modules | Direct moves, update imports |
| Rename files | LOW | Direct callers | Grep + update |

## Proposed Target Structure

```
app/
├── __init__.py
├── core/                     # Infrastructure
│   ├── __init__.py
│   ├── config.py             # Settings
│   ├── db.py                 # Database session
│   └── exceptions.py         # Custom exceptions
├── models/                   # ORM models (split by domain)
│   ├── __init__.py           # Re-exports all models (backward compat)
│   ├── base.py               # Base class + enums
│   ├── user.py               # User, Session, API keys
│   ├── player.py             # Player, StatSnapshot, Percentile
│   ├── team.py               # Team, League, Fixture
│   ├── workspace.py          # Shortlist, Entry, Note, Tag
│   ├── billing.py            # Subscription, Webhook
│   ├── org.py                # Organization, Membership
│   ├── transfer.py           # MarketValuation, TransferHistory
│   ├── tactical.py           # MatchPassingNetwork, etc.
│   ├── watch.py              # Watch, Alert, Preferences
│   ├── search.py             # SavedSearch, SearchHistory
│   ├── report.py             # Report, ReportQuota
│   ├── assistant.py          # AssistantQuota
│   ├── emerging.py           # EmergingPlayerScore
│   ├── dashboard.py          # DashboardState, SavedPlayers
│   ├── coverage.py           # DataCoverage, IngestionAnomaly
│   └── activity.py           # ActivityLog
├── security/                 # Auth primitives
│   ├── __init__.py
│   ├── auth.py               # Password hashing, sessions
│   ├── api_keys.py           # API key management
│   └── deps.py               # require_user dependency
├── api/                      # API layer
│   ├── __init__.py
│   ├── app.py                # FastAPI app factory (from main.py)
│   └── routes/               # Domain-organized routes
│       ├── __init__.py
│       ├── auth.py           # Login/register/profile
│       ├── billing.py        # Stripe checkout/webhook
│       ├── workspace.py      # Shortlists
│       ├── search.py         # Structured search
│       ├── reports.py        # AI reports
│       ├── watch.py          # Watchlist/alerts
│       ├── dashboard.py      # Dashboard
│       ├── org.py            # Organizations
│       ├── transfer.py       # Transfer intelligence
│       ├── tactical.py       # Tactical analysis
│       ├── public.py         # Public API
│       ├── players.py        # Player endpoints
│       ├── teams.py          # Team endpoints
│       ├── leagues.py        # League endpoints
│       └── misc.py           # Coverage, methodology, positions
├── queries/                  # Data access (keep flat — already clean)
├── compute/                  # Computation (keep flat — already clean)
├── sources/                  # Data sources (keep flat — already clean)
├── orchestration/            # Pipeline orchestration
├── notifications/            # Email delivery
├── watch/                    # Watchlist detection
├── reports.py                # Report generation
├── report_export.py          # Export logic
├── reconciliation.py         # Name reconciliation
├── activity.py               # Activity logging
├── assistant.py              # AI assistant
├── billing.py                # Stripe integration
├── config/                   # JSON config
└── schema.sql                # DDL
```

## Migration Strategy

### Phase 1: Split models.py (backward-compatible)
- Create `app/models/` directory
- Move each model group to its own file
- Keep `app/models.py` as backward-compatible re-export shim
- Verify: all 478 tests pass

### Phase 2: Organize API routes (backward-compatible)
- Create `app/api/routes/` directory
- Move view files to routes/
- Update `main.py` to import from new locations
- Keep old imports working via `__init__.py`
- Verify: all 478 tests pass

### Phase 3: Extract security module
- Move auth.py, api_keys.py, deps.py to security/
- Update imports
- Verify: all 478 tests pass

### Phase 4: Documentation
- Generate architecture docs
- Update file move ledger
