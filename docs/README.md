# Statlas — Documentation Index

This is the single home for all Statlas documentation. The repo previously split
docs between `docs/` and `project-docs/`; the two are now merged here (2026-08-14),
with the full project-documentation suite under [suite/](suite/).

**Start here:** [suite/DOC-SUITE-MAP.md](suite/DOC-SUITE-MAP.md) (suite map + how the
14 suite files cross-link) → [suite/PRD.md](suite/PRD.md) → [suite/Tracker.md](suite/Tracker.md).

## Structure

```
docs/
├── README.md                      ← this index
├── CONSTITUTION.md                master product constitution (data-honesty, §7 DoD)
├── CONTRIBUTING.md                environment setup, conventions, CI expectations
├── suite/                         ← the 14-file project-documentation suite + map
│   ├── DOC-SUITE-MAP.md           suite overview + consistency report
│   ├── PRD.md                     product requirements (personas, REQs, KPIs)
│   ├── TechSpec.md                architecture, stack, NFRs, integrations
│   ├── AppFlow.md                 screens, states, journeys
│   ├── Design.md                  design tokens, components, a11y (design-system +
│   │                              component-states-spec consolidated here)
│   ├── Schema.md                  data model (ER, tables, indexes, migrations)
│   ├── ImplementationPlan.md      phased build plan (Phases 0–4)
│   ├── Tracker.md                 live status dashboard (single source of truth)
│   ├── Rules.md                   engineering + AI-agent operating rules
│   ├── API.md                     every /api/v1 endpoint
│   ├── SecurityAndCompliance.md   threat model, compliance checklist
│   ├── Testing.md                 test pyramid, gates, e2e matrix
│   ├── Deployment.md              environments, CI/CD, rollback
│   ├── Glossary.md                shared vocabulary
│   └── RiskRegister.md            risks, mitigations, owners
├── analytics/                     Phase 0/1 data rules (source of truth for the suite)
│   ├── methodology.md             Statlas Index formula, weights, threshold
│   ├── percentile-rules.md        grouping (tier), cadence, immutability
│   ├── similarity-explanation-method.md  how "similar players" explanations work (Phase 6)
│   ├── emerging-player-methodology.md  Phase 11 emerging-player score formula, weights, thresholds
│   ├── data-compliance-notes.md   per-source license/ToS/rate-limit review
│   └── production-validation-log.md  real scrape validation + dataset-mode decision
├── product/                       Phase 7/8/9/10/11 scouting workspace + query builder + reports + alerts + leagues
│   ├── scouting-pipeline.md       status pipeline rules, transitions, integrity, authz
│   ├── query-builder-scope.md     Phase 8 condition grammar, AND-only scope, floor, missing-data rules
│   ├── scouting-reports.md        Phase 9 report structure, confidence rules, risk rules, verification design
│   ├── alert-trigger-definitions.md  Phase 10 exact trigger thresholds, non-triggers, follow granularity
│   ├── notification-delivery.md   Phase 10 provider choice, preference compliance, digests, unsubscribe
│   ├── league-page-spec.md        Phase 11 league hub page structure, URL scheme, honest degradation rules
│   ├── dashboard-scope.md         Phase 13 dashboard layout decision, widget order, data freshness
│   └── dashboard-recommendations-logic.md  Phase 13 trending + recommendation heuristics, formulas, limitations
├── api/                           live API verification (BLOCKED, Part A3)
│   └── live-verification-log.md   real captured endpoint evidence or BLOCKED status
├── ai-assistant/                  live AI-assistant verification (BLOCKED, Part A2)
│   └── live-verification-log.md   real captured traces or BLOCKED status
├── engineering/                   unique engineering records
│   ├── infra-plan.md              staging + backup strategy
│   ├── performance-baseline.md    Lighthouse LCP baseline (572–740ms)
│   ├── postgres-parity-notes.md   Postgres 17 parity proof
│   ├── timezone-policy.md         UTC policy (DTZ-enforced)
│   ├── cleanup-audit-2026-08-14.md  repo cleanup audit
│   ├── phase3-verification-log.md   Phase 3 (trend/maps/sharing) audit — every
│   │                               Part A–D item mapped to code + tests
│   ├── phase4-security-review.md   Phase 4 payment/API-key security review (D3)
│   ├── watch-detection-scaling-notes.md  Phase 10 batch-query strategy + scaling path
│   ├── account-system-audit.md    Phase 12 account system audit (Path 1 — additive build)
│   └── auth-policy.md             Phase 12 auth policy (password, session, rate-limit, deletion)
├── billing/                       Phase 4 billing
│   ├── pricing-config.md          tier boundaries + Stripe Products/Prices map
│   └── live-verification-log.md   live Stripe verification or BLOCKED status (Part A1)
├── launch/                        Phase 5 soft launch + iteration
│   ├── soft-launch-plan.md        audience, explicit goal, bounded scope, triage SLA, go/no-go criteria
│   ├── launch-post.md             the announcement text (ready to post)
│   ├── dogfood-log.md             internal dogfooding record (real findings, 0 blockers)
│   ├── feedback-triage-log.md     execution record + triage log + go/no-go decision
│   └── iteration-cadence.md       post-launch weekly cadence + refresh transparency (C3/C4)
└── legal/                         legal drafts + founder checklist
    ├── terms-of-service-draft.md  DRAFT — REQUIRES LAWYER REVIEW
    ├── privacy-policy-draft.md    DRAFT — REQUIRES LAWYER REVIEW
    ├── founder-legal-checklist.md entity/domain/email/trademark checklist
    └── pre-launch-human-actions.md  tracked, owned human-action list (all ⬜ pending)
```

## What was merged / removed (2026-08-14)

- **Moved:** `project-docs/*` → `docs/suite/` (15 files, internal links intact).
- **Removed (superseded by suite):** `design/design-system.md`, `design/component-states-spec.md` (→ `suite/Design.md`); `product/site-map.md`, `product/navigation-and-flows.md` (→ `suite/AppFlow.md` + `suite/PRD.md`); `guides/phase2.md` (→ `suite/ImplementationPlan.md`), `guides/testing.md` (→ `suite/Testing.md`); `engineering/architecture.md` (→ `suite/TechSpec.md`).
- **Removed (historical one-time records):** `engineering/analysis_report.md`, `engineering/migration_summary.md`, `engineering/folder_structure.md`, `engineering/module_dependency.md`, `engineering/package_overview.md`, `engineering/startup_flow.md`, `engineering/cleanup-audit-2026-08-13.md` (superseded by the 08-14 audit).

## Guidance

| You want... | Read |
|---|---|
| What we're building & why | [suite/PRD.md](suite/PRD.md) |
| How it's built | [suite/TechSpec.md](suite/TechSpec.md) |
| Screens/states/user journeys | [suite/AppFlow.md](suite/AppFlow.md) |
| Visual system / tokens | [suite/Design.md](suite/Design.md) + `web/styles/tokens.css` |
| Data model | [suite/Schema.md](suite/Schema.md) + `app/schema.sql` |
| Build plan | [suite/ImplementationPlan.md](suite/ImplementationPlan.md) |
| What's done / next / stuck | [suite/Tracker.md](suite/Tracker.md) |
| Coding + AI-agent rules | [suite/Rules.md](suite/Rules.md) |
| API reference | [suite/API.md](suite/API.md) |
| Testing / gates | [suite/Testing.md](suite/Testing.md) |
| Deploy / rollback | [suite/Deployment.md](suite/Deployment.md) |
| Risks / blockers | [suite/RiskRegister.md](suite/RiskRegister.md) |
| Statlas Index formula | [analytics/methodology.md](analytics/methodology.md) |
| Soft-launch plan / go-no-go | [launch/soft-launch-plan.md](launch/soft-launch-plan.md) |
| Post-launch cadence | [launch/iteration-cadence.md](launch/iteration-cadence.md) |
| Compliance / legal status | [legal/pre-launch-human-actions.md](legal/pre-launch-human-actions.md) |
| Scouting pipeline rules | [product/scouting-pipeline.md](product/scouting-pipeline.md) |
| Query-builder grammar/scope | [product/query-builder-scope.md](product/query-builder-scope.md) |
| Scouting report design / confidence / risks | [product/scouting-reports.md](product/scouting-reports.md) |
| Alert trigger definitions / thresholds | [product/alert-trigger-definitions.md](product/alert-trigger-definitions.md) |
| Notification delivery / preferences | [product/notification-delivery.md](product/notification-delivery.md) |
