# Statlas Folder Structure

## Root Directory

```
Statlas/
├── app/                    # Python backend (FastAPI)
├── web/                    # Frontend (Next.js)
├── tests/                  # Python tests
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── data/                   # Runtime data (gitignored except coverage_matrix.json)
├── assets/                 # Static assets (logo)
├── .github/                # CI/CD workflows
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Python backend container
├── pyproject.toml          # Python project config
├── requirements.txt        # Python dependencies
├── pytest.ini              # Test configuration
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── .pre-commit-config.yaml # Pre-commit hooks
├── README.md               # Project README
├── LICENSE                 # MIT License
├── CONTRIBUTING.md         # Contribution guidelines
├── SECURITY.md             # Security policy
└── PROJECT_OVERVIEW.md     # High-level project overview
```

## `app/` — Python Backend

```
app/
├── __init__.py             # Package marker
├── api/                    # API layer (thin controllers)
│   ├── __init__.py
│   ├── main.py             # FastAPI app factory + router registration
│   ├── deps.py             # Shared dependencies (require_user)
│   ├── archetype_views.py  # Archetype endpoints
│   ├── assistant_views.py  # AI assistant endpoints
│   ├── billing_views.py    # Auth + Stripe billing endpoints
│   ├── comment_views.py    # Comment endpoints
│   ├── dashboard_views.py  # Dashboard endpoints
│   ├── e2e_views.py        # E2E test helpers
│   ├── org_views.py        # Organization endpoints
│   ├── player_view.py      # Player profile endpoints
│   ├── public_views.py     # Public API (API key auth)
│   ├── registry_view.py    # Methodology metadata
│   ├── report_views.py     # AI report endpoints
│   ├── search_views.py     # Search endpoints
│   ├── tactical_views.py   # Tactical analysis endpoints
│   ├── transfer_views.py   # Transfer intelligence endpoints
│   ├── watch_views.py      # Watchlist endpoints
│   └── workspace_views.py  # Workspace endpoints
├── compute/                # Business logic & computations
│   ├── __init__.py
│   ├── anomaly_check.py    # Data quality anomaly detection
│   ├── clustering.py       # ML player archetypes (KMeans)
│   ├── emerging.py         # Emerging player score computation
│   ├── formation.py        # Formation detection from events
│   ├── index.py            # Statlas Index calculation
│   ├── market_validation.py # Market data validation rules
│   ├── opportunity.py      # Hidden gems, position scarcity
│   ├── passing_network.py  # Network graph analysis
│   ├── percentiles.py      # Fractional-rank percentile computation
│   ├── risk.py             # Transfer risk assessment
│   └── spatial_analysis.py # Zone heatmaps, pressure maps
├── config/                 # JSON configuration files
│   ├── metric_registry.json # Metric definitions, weights, formulas
│   ├── pricing.json        # Subscription plan limits
│   ├── search_presets.json # Curated search templates
│   └── tiers.json          # League tier assignments
├── notifications/          # Email delivery
│   └── email.py            # Resend email adapter
├── orchestration/          # Pipeline automation
│   ├── __init__.py
│   ├── event_link.py       # Event-to-player reconciliation
│   └── weekly_refresh.py   # Weekly data refresh pipeline
├── queries/                # Data access layer
│   ├── __init__.py
│   ├── archetype_queries.py # Archetype queries
│   ├── coverage_queries.py  # Data coverage queries
│   ├── dashboard_queries.py # Dashboard aggregation
│   ├── emerging_queries.py  # Emerging player queries
│   ├── event_queries.py     # Shot/pass map queries (coverage-gated)
│   ├── leaderboard_queries.py # Leaderboard filtering
│   ├── league_page_queries.py # League hub queries
│   ├── league_queries.py    # League catalog queries
│   ├── market_queries.py    # Market data queries
│   ├── org_queries.py       # RBAC, membership, audit queries
│   ├── player_queries.py    # Player profile queries
│   ├── sentences.py         # Data-driven sentence generation
│   ├── similar_players.py   # Explainable similarity
│   ├── structured_search.py # Multi-condition query execution
│   ├── team_queries.py      # Team profile queries
│   ├── transfer_queries.py  # Transfer candidate queries
│   ├── trend_queries.py     # Time-series trend queries
│   ├── watch_queries.py     # Watch/alert queries
│   └── workspace_queries.py # Workspace CRUD queries
├── sources/                # External data source adapters
│   ├── __init__.py
│   ├── api_football.py     # API-Football adapter
│   ├── base.py             # StatsSource ABC + HTTP infrastructure
│   ├── fbref.py            # FBref scraper
│   ├── market_data.py      # Fixture market data source
│   ├── statsbomb.py        # StatsBomb Open Data adapter
│   └── understat.py        # Understat scraper
├── watch/                  # Watchlist detection & delivery
│   ├── delivery.py         # Alert delivery (email, in-app)
│   └── detection.py        # Alert trigger detection
├── activity.py             # Activity logging (60s dedup)
├── api_keys.py             # API key management
├── assistant.py            # AI assistant (Anthropic)
├── auth.py                 # Authentication (PBKDF2, sessions)
├── billing.py              # Stripe billing integration
├── cli.py                  # CLI entry point
├── config.py               # Settings & environment variables
├── db.py                   # Database session management
├── models.py               # All ORM models (30+ classes)
├── reconciliation.py       # Name reconciliation across sources
├── report_export.py        # Report export (PDF/JSON/CSV)
├── reports.py              # AI report generation
└── schema.sql              # PostgreSQL DDL (canonical schema)
```

## `web/` — Frontend (Next.js)

```
web/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   ├── globals.css         # Global styles
│   ├── not-found.tsx       # 404 page
│   ├── (embed)/            # Embed routes (radar, trend)
│   ├── about/              # About page
│   ├── account/            # Account settings
│   ├── api-docs/           # API documentation
│   ├── archetypes/         # ML archetypes
│   ├── changelog/          # Changelog
│   ├── clubs/              # Team profiles
│   ├── compare/            # Compare tool
│   ├── dashboard/          # Personal dashboard
│   ├── data-coverage/      # Coverage matrix
│   ├── help/               # Help page
│   ├── leagues/            # League hub pages
│   ├── legal/              # Legal pages (ToS, Privacy)
│   ├── login/              # Login page
│   ├── methodology/        # Methodology documentation
│   ├── orgs/               # Organization management
│   ├── players/            # Player profiles
│   ├── positions/          # Leaderboards
│   ├── pricing/            # Pricing page
│   ├── register/           # Registration page
│   ├── reports/            # AI reports
│   ├── reset-password/     # Password reset
│   ├── search/             # Structured search
│   ├── tactical/           # Tactical analysis
│   ├── transfers/          # Transfer intelligence
│   ├── trend/              # Trend analysis
│   ├── watchlist/          # Watchlist & alerts
│   └── workspace/          # Scouting workspace
├── components/             # Reusable React components (35)
│   ├── AddToShortlist.tsx
│   ├── Assistant.tsx
│   ├── AuthProvider.tsx
│   ├── Breadcrumbs.tsx
│   ├── CompareTool.tsx
│   ├── DatasetBanner.tsx
│   ├── EmbedRadar.tsx
│   ├── EmbedTrend.tsx
│   ├── EventMaps.tsx
│   ├── FollowButton.tsx
│   ├── Footer.tsx
│   ├── GenerateReport.tsx
│   ├── Header.tsx
│   ├── KeyStats.tsx
│   ├── LeaderboardTable.tsx
│   ├── LegalDoc.tsx
│   ├── NotificationBell.tsx
│   ├── OrgSelector.tsx
│   ├── PassMap.tsx
│   ├── Pitch.tsx
│   ├── PlayerArchetypeSection.tsx
│   ├── PlayerTransferSection.tsx
│   ├── RadarCard.tsx
│   ├── RadarChart.tsx
│   ├── RecencyLine.tsx
│   ├── ReportIssue.tsx
│   ├── SearchCombobox.tsx
│   ├── SharePanel.tsx
│   ├── ShotMap.tsx
│   ├── SimilarPlayers.tsx
│   ├── SquadRadar.tsx
│   ├── ThemeToggle.tsx
│   ├── TrendCard.tsx
│   ├── TrendChart.tsx
│   └── TrendTool.tsx
├── lib/                    # Utility modules
│   ├── alertFormat.ts      # Alert formatting
│   ├── api.ts              # API client functions
│   ├── chartSvg.ts         # SVG chart rendering
│   ├── colors.ts           # Design token colors
│   ├── format.ts           # Number/date formatting
│   ├── ogRender.tsx        # OG image rendering
│   ├── radar.ts            # Radar chart data processing
│   ├── share.ts            # URL state management
│   ├── trend.ts            # Trend data processing
│   ├── types.ts            # TypeScript type definitions
│   └── workspace.ts        # Workspace utilities
├── e2e/                    # Playwright E2E tests
├── styles/                 # CSS
│   └── tokens.css          # Design tokens
├── scripts/                # Build scripts
│   └── e2e-server.sh       # E2E test server
├── next.config.mjs         # Next.js configuration
├── tsconfig.json           # TypeScript configuration
├── package.json            # Node.js dependencies
├── playwright.config.ts    # Playwright configuration
├── lighthouserc.json       # Lighthouse CI configuration
└── Dockerfile              # Frontend container
```

## `tests/` — Python Tests

```
tests/
├── __init__.py
├── conftest.py             # Shared fixtures (in-memory SQLite)
├── fixtures/               # Test data files
│   ├── api_football_fixtures.json
│   ├── fbref_league.html
│   ├── statsbomb_competitions.json
│   ├── statsbomb_events.json
│   ├── statsbomb_matches.json
│   ├── understat_api_players.json
│   └── understat_page.html
├── test_accounts.py        # Account system tests
├── test_anomaly.py         # Anomaly detection tests
├── test_api.py             # API endpoint tests
├── test_api_football.py    # API-Football source tests
├── test_assistant.py       # AI assistant tests
├── test_base.py            # Base source tests
├── test_billing.py         # Billing tests
├── test_clustering.py      # Clustering tests
├── test_dashboard.py       # Dashboard tests
├── test_event_queries.py   # Event query tests
├── test_fbref.py           # FBref source tests
├── test_idempotency.py     # Idempotency tests
├── test_index.py           # Index computation tests
├── test_integration.py     # Integration tests
├── test_league_hub.py      # League hub tests
├── test_matrix_validation.py # Matrix validation tests
├── test_org.py             # Organization tests
├── test_percentiles.py     # Percentile computation tests
├── test_phase2_queries.py  # Phase 2 query tests
├── test_public_api.py      # Public API tests
├── test_reconciliation.py  # Reconciliation tests
├── test_reports.py         # Report tests
├── test_sentences.py       # Sentence generation tests
├── test_similarity_explanation.py # Similarity tests
├── test_statsbomb.py       # StatsBomb source tests
├── test_structured_search.py # Search tests
├── test_tactical.py        # Tactical analysis tests
├── test_tier_completeness.py # Tier completeness tests
├── test_transfer_intelligence.py # Transfer tests
├── test_trend.py           # Trend tests
├── test_understat.py       # Understat source tests
├── test_watch.py           # Watchlist tests
└── test_workspace.py       # Workspace tests
```

## `docs/` — Documentation

```
docs/
├── architecture.md         # System architecture
├── folder_structure.md     # This file
├── API_DOCUMENTATION.md    # API reference
├── CONTRIBUTING.md         # Contribution guidelines
├── CONSTITUTION.md         # Project constitution
├── DEVELOPER_GUIDE.md      # Developer setup guide
├── README.md               # Docs index
├── migration_summary.md    # Migration summary
├── analytics/              # Analytics documentation
├── api/                    # API documentation
├── audit/                  # Audit reports
├── billing/                # Billing documentation
├── engineering/            # Engineering documentation
├── launch/                 # Launch documentation
├── legal/                  # Legal documents
├── ml/                     # ML documentation
├── product/                # Product documentation
└── suite/                  # Documentation suite
```

## `scripts/` — Utility Scripts

```
scripts/
├── audit_sentences.py      # Sentence audit script
├── feedback.py             # Feedback collection
├── seed_dev_db.py          # Development database seeder
├── validate_search_presets.py # Search preset validator
├── verify_reports.py       # Report verification
├── verify_similarity_explanations.py # Similarity verification
└── migrations/             # Database migrations
    └── 001_percentile_tier_key.sql
```
