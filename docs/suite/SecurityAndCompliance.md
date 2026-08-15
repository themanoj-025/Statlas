# SecurityAndCompliance.md — Statlas Security & Compliance

| Field | Value |
|---|---|
| Version | v0.1 |
| Last Updated | 2026-08-14 |
| Owner | Security + Founder |
| Status | In Review |

## 1. Threat Model (STRIDE)

| Threat | Asset | Mitigation | Status |
|---|---|---|---|
| **S**poofing | API endpoints | No auth surfaces in v1 (public read-only) — low risk; Phase 4 adds keys | ⚪ Phase 4 |
| **T**ampering | Snapshot data integrity | Immutable rows; anomaly gate before publish; tests assert no updates | ✅ |
| **R**epudiation | Scrape provenance | scrape_date + source versioning; production-validation-log | ✅ |
| **I**nformation disclosure | Player PII (DOB) | DOB never logged; not exposed beyond profile | ✅ |
| **D**enial of service | Upstream scrapers | Self-imposed rate limits + budget tracker (API-Football 80/day) | ✅ |
| **E**levation of privilege | Admin/CLI | CLI is local-only; no privileged endpoints in prod | ✅ |

## 2. Assets & Data Classification

| Class | Examples | Handling |
|---|---|---|
| Public | stats, percentiles, index, coverage | Read-only API; no access control |
| PII (indirect) | players.date_of_birth | Not logged; rendered as computed age only |
| Secrets | `API_FOOTBALL_KEY`, `POSTGRES_PASSWORD` | Env vars only; gitleaks + gitignore; never in code/docs |
| Legal drafts | ToS/Privacy | Committed as DRAFT with review flags (not secrets) |

## 3. Security Controls

| Control | Where | Enforcement |
|---|---|---|
| Secret scanning | CI job `security` | gitleaks/gitleaks-action@v2 — fails on any finding |
| Dependency vulns | CI python + web jobs | `pip-audit` + `npm audit --audit-level=high` — fail on high+ |
| Input validation | API layer | Pydantic + query validators (e.g., `limit ≤ 25`) |
| No raw SQL concat | `app/queries/*` | SQLAlchemy only; reviewed pattern |
| Timezone correctness | backend | ruff DTZ rule (no naive datetime) |
| A11y/security UX | frontend | axe CI (0 violations); honest error states |
| Upstream rate limits | `app/sources/*` | config-driven delays (compliance notes) |

## 4. Secrets Management

- All secrets via environment variables (`.env.example` documents names + defaults; `.env` gitignored).
- Rotation policy: any leaked secret is rotated immediately; deletion from files does **not** remove it from history — assume compromised.
- Phase 4: Stripe keys, API keys stored server-side only; never in client bundles.

## 5. Dependency & Supply Chain

- Dependabot configured for weekly dependency updates.
- Known pinned override: `@puppeteer/browsers@^3.2.0` + `tmp@^0.2.6` in `web/package.json` `overrides` — resolves GHSA-jmr9-qjv8-65gv (`extract-zip`, no patched version) in the `@lhci/cli` tree (RISK-05).
- Upgrade policy: minor/patch auto; major requires verification (Rules §6).

## 6. Compliance Checklist

| Item | Requirement | Status |
|---|---|---|
| ToS draft exists | `docs/legal/terms-of-service-draft.md` | ✅ draft — **lawyer review ⬜ pending** |
| Privacy draft exists | `docs/legal/privacy-policy-draft.md` (Stripe as sub-processor, GDPR/UK GDPR flagged) | ✅ draft — **lawyer review ⬜ pending** |
| Founder legal checklist | entity, domain, email, trademark (`founder-legal-checklist.md`) | ✅ doc — **execution ⬜ pending** |
| StatsBomb license re-verify | bespoke user agreement — non-commercial; **§1.2.2 bans commercial exploitation of data and derived analysis → conflicts with Pro-gated shot/pass maps** (re-verified 2026-08-15; data-compliance-notes.md §3) | 🔴 hard blocker for Phase 4 |
| FBref redistribution | no commercial license → publish derived metrics only (percentiles/index), not raw tables | ✅ design constraint |
| API-Football ToS | free-tier limits documented; budget tracker | ✅ |
| GDPR posture | no EU PII collected in v1; revisit at Phase 4 (accounts) | ⚪ Phase 4 |
| Human action tracking | `docs/legal/pre-launch-human-actions.md` (owned, statused) | ✅ created — items ⬜ |

## 7. Privacy-by-Design (v1)

- No accounts, no emails, no cookies beyond theme preference (localStorage), no analytics SDK embedded.
- Analytics plan: privacy-respecting (no cross-site tracking) — decision flagged in privacy-policy-draft.md; not yet implemented.
- Data retention: no user data collected → N/A pre-Phase 4.

## 8. Incident Response Plan (outline)

1. **Detect** — CI red, uptime check (planned), user report.
2. **Contain** — rotate secrets (if any), disable access, revert deploy (Deployment.md §4 rollback).
3. **Eradicate** — remove cause, patch, verify.
4. **Recover** — redeploy from clean state; restore DB from backup (backup strategy: docs/engineering/infra-plan.md).
5. **Post-mortem** — document in Tracker.md changelog + engineering docs.

SLA/on-call: N/A pre-launch (solo founder); revisit Phase 4.

## 9. Related Documents

| Document | Relationship |
|---|---|
| [PRD.md](PRD.md) | Trust features (REQ-015/016/017) |
| [TechSpec.md](TechSpec.md) | §6 NFR security row |
| [AppFlow.md](AppFlow.md) | N/A |
| [Design.md](Design.md) | A11y compliance |
| [Schema.md](Schema.md) | §10 sensitive data map |
| [ImplementationPlan.md](ImplementationPlan.md) | Phase 4 entry gates (RISK-01/03/04) |
| [Tracker.md](Tracker.md) | Compliance item status |
| [Rules.md](Rules.md) | §6 security baseline |
| [API.md](API.md) | No-auth posture + Phase 4 plan |
| [Testing.md](Testing.md) | Security-relevant test gates |
| [Deployment.md](Deployment.md) | Secure deploy + rollback |
| [Glossary.md](Glossary.md) | Terms |
| [RiskRegister.md](RiskRegister.md) | RISK-03/04/05 |
