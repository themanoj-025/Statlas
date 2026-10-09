# Deployment.md — Statlas Environments & Deployment

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-14 |
| Owner | DevOps |
| Status | In Review (staging/prod not yet built — see §5) |

## 1. Environments

| Env | URL | Data | Deploy trigger |
|---|---|---|---|
| Local dev | `127.0.0.1:3000` + `:8000` | SQLite fixture-demo (`data/dev.db`) | manual |
| CI | ephemeral per-run | fresh seed per run | every push/PR |
| Staging (planned) | `staging.statlas.com` | Postgres staging | manual promote from green main |
| Prod (planned) | `statlas.com` | Postgres, production dataset | CI green → deploy |

Staging + prod are **planned, not built** — infra-plan.md documents the design (hosting, backups, domain, TLS). This section is the target design.

## 2. CI/CD Pipeline

```mermaid
flowchart LR
    A[push / PR] --> B[python: pytest+ruff+pip-audit]
    A --> C[security: gitleaks]
    A --> D[web: tsc + npm audit + build + Playwright]
    A --> E[lighthouse: LCP < 2.5s]
    B & C & D & E --> F{all green?}
    F -->|no| G[fix and re-push]
    F -->|yes| H[merge to main]
    H --> I[deploy web image (standalone)]
    I --> J[run migrations]
    J --> K[smoke: health + key routes 200]
```

## 3. Build & Runtime

- **API image** (`Dockerfile`): `python:3.14-slim`, non-root, `uvicorn app.api.main:app` on :8000.
- **Web image** (`web/Dockerfile`): multi-stage (`deps` → `builder` → `runner`), Next.js **standalone** output for slim production image; `npm run start`.
- **Compose** (`docker-compose.yml`): services `db` (postgres), `api`, `web`, `seed` (opt-in profile `seed` — `docker compose --profile seed run --rm seed`).
- **Env wiring:** `NEXT_PUBLIC_STATLAS_API_URL` baked at build time from `STATLAS_PUBLIC_API_URL` (docker-compose); `DATABASE_URL` for API.

## 4. Rollback Procedure

1. Detect bad release (CI smoke, LCP regression, user report).
2. **Revert the deploy** to previous known-green image tag (web standalone image is immutable per tag; API image likewise).
3. DB: migrations are forward-only + additive — a rollback of code does not require schema rollback; if a bad migration ran, apply its documented reverse (`scripts/migrations/`), never edit applied files.
4. Verify health + smoke; log in Tracker.md changelog.

## 5. Feature Flags & Canary

- v1: no feature flags (no accounts). Dataset-mode banner serves as the honest "flag" for fixture vs production data.
- Staging→prod: manual promote; no canary pre-launch (solo founder). Phase 4 may add canary % for billing rollout.

## 6. Runbook Basics

| Situation | Action |
|---|---|
| API down | check uvicorn logs; restart container; verify DATABASE_URL |
| Web 500 on SSR | check API reachability from web env; `NEXT_PUBLIC_STATLAS_API_URL` correctness (baked at build) |
| LCP regression | Lighthouse CI report → diff images/payloads; check SSR data payload size |
| DB backup restore | Postgres backup (strategy in infra-plan.md); restore to staging first |
| Scrape failed | weekly_refresh logs; anomaly gate holds publish until resolved; check source rate-limit/403 (RISK-01) |

## 7. Monitoring (planned)

- Uptime check + Lighthouse CI trend; `STATLAS_LOG_LEVEL` structured logs; Grafana/pg metrics per infra-plan.md. Not yet implemented (pre-launch scope).

## 8. Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Release criteria enforced here |
| [TechSpec.md](TechSpec.md) | §7 environments, Docker images |
| [AppFlow.md](AppFlow.md) | Smoke routes |
| [Design.md](Design.md) | N/A |
| [Schema.md](Schema.md) | §7 migrations at deploy |
| [ImplementationPlan.md](ImplementationPlan.md) | Rollout strategy §6 |
| [Tracker.md](Tracker.md) | Deploy history |
| [Rules.md](Rules.md) | CI gates §3 |
| [API.md](API.md) | Base URLs per env |
| [SecurityAndCompliance.md](SecurityAndCompliance.md) | §8 incident response + rollback |
| [Testing.md](Testing.md) | Gates that must pass pre-deploy |
| [Glossary.md](Glossary.md) | Terms |
| [RiskRegister.md](RiskRegister.md) | Deploy-related risks |
