# Statlas — Ultra Master Cleanup Audit (2026-08-14)

Date: 2026-08-14 · Scope: full repo (backend `app/`, frontend `web/`, tests, docs, CI, infra) at commit `b68ce48`.
Method: Phase A inventory + baseline → Phase B detection (grep for AI fingerprints, debug artifacts, boilerplate, dead code, secrets; AST scan for unused Python functions; CSS-class cross-reference; dependency cross-check against imports) → Phase C triage into Tier 0–3 → Phase D remediation in batches with validation after each → Phase E diff review + this report.

---

## Executive Summary

Scope: full-repo artifact/boilerplate/dead-code audit. Effort: ~1 working pass with verification after each batch. Overall risk: **low**. All changes were Tier 0/1 mechanical removals (dead function, dead CSS classes, broken npm script, stale doc commands) — no behavior, API contract, route, or schema changed. The repo is in strong shape: zero AI fingerprints, zero debug artifacts, zero secrets, no orphaned components/pages, no duplicate utilities. Full suite green before and after (104 pytest, 12 node tests, tsc clean, ruff clean, production build succeeds).

## AI/Template Artifacts Removed

**None found.** Fingerprint scan (attribution phrases, vendor names, prompt fragments, conversational filler) across `app/`, `web/`, `scripts/`, `tests/` returned zero matches. Legitimate "AI" references (OpenAI API calls, AI-assisted-commit footers) are accurate technical documentation and were preserved per Section 4/19.

## Dead Code Removed

- **`app/config.py` — `set_settings()`** (function, ~4 lines): test hook defined but never called anywhere in `app/`, `tests/`, or `scripts/` (verified via AST call-graph scan + grep). Removed.
- **`web/app/globals.css` — `.container--md`** (CSS class): defined but zero usages in any `.tsx`/`.ts` (verified cross-reference, including template-literal classNames).
- **`web/app/globals.css` — `.grid__span-2`** (CSS class): defined but zero usages (only 3/4/6/8 are used in the grid).
- **`web/app/globals.css` — `.grid__span-12`** (CSS class): defined but zero usages.

Verified NOT dead (kept): `resolve_anomaly`, `verify_index_consistency` (both covered by tests); `has_source_coverage` (tested query-layer helper); `get_league_teams` (see Tier 2 below); all web component exports (every component has ≥1 import site — the earlier "0 refs" results were relative-import artifacts); all `web/lib` exports used.

## Duplicate Code Removed/Consolidated

**None found.** Format helpers centralized in `web/lib/format.ts` (no duplicated formatters in components). No duplicate utility functions, validation logic, or constants detected across the codebase.

## Debug Artifacts Removed

**None found.** No `console.log`/`console.debug`/`debugger;` in web app code (all `print()` calls are in CLI scripts `app/cli.py` / `scripts/seed_dev_db.py`, which are legitimate CLI output). No commented-out code blocks, no debug banners, no test-only hacks in production paths.

## Documentation Cleaned

- **`docs/guides/phase2.md`** — corrected stale uvicorn command `uvicorn api.main:app` → `uvicorn app.api.main:app` (the actual module path used by `Dockerfile` and `README.md`).
- **`docs/CONTRIBUTING.md`** — same stale command corrected.

> 📝 **Note (2026-08-14 docs merge):** `docs/guides/phase2.md` and `docs/engineering/startup_flow.md` were later consolidated into `docs/suite/` (ImplementationPlan.md / TechSpec.md) and removed — see `docs/README.md` "What was merged / removed".

Verified accurate (kept): README test counts (104 pytest / 12 node / 9 e2e), env var tables, architecture docs; `docs/engineering/*` dated documents are historical records and remain accurate as-of-date.

## Dependencies Removed

**None removed.** All Python deps in `requirements.txt` are imported or tooling-required (verified per-package). All npm deps in `package.json` are imported except `lighthouse` — see Tier 2 below.

## Configuration Improvements

- **`web/package.json`** — removed the broken `"lint": "next lint"` script. Next.js 16 removed the `next lint` command; the script errored ("Invalid project directory provided") while misleadingly exiting 0. It was referenced by nothing (CI runs `tsc --noEmit` + build; no docs mention it). No ESLint config or dependency exists in the project, so a non-functional script was removed rather than left as a false-green gate. **Recommendation:** add real ESLint (flat config + `eslint-plugin-react-hooks`/`@next/eslint-plugin-next`) in a separate change if linting is desired.

## Security Improvements

**None required.** Secret scan (API keys, tokens, passwords, private keys) across `app/`, `web/`, `scripts/` found zero hardcoded credentials — the only hits were design tokens and legal-policy copy. `npm audit --audit-level=high` and `pip-audit` gates pass (audit-gate status re-verified during this pass). gitleaks runs in CI.

## Performance Improvements

**None applicable.** No unused large libraries removable (the one candidate, `lighthouse`, is a dev-only tool dependency — see Tier 2). No speculative rewrites performed per Section 18.

## Files Modified

- `app/config.py` (removed `set_settings`)
- `web/app/globals.css` (removed 3 dead classes)
- `web/package.json` (removed broken `lint` script)
- `docs/guides/phase2.md` (corrected uvicorn path; file later removed in the 2026-08-14 docs merge → `docs/suite/`)
- `docs/CONTRIBUTING.md` (corrected uvicorn path)
- `docs/engineering/cleanup-audit-2026-08-14.md` (this report)

## Files Deleted

**None.**

## Validation Results

| Check | Before | After |
|---|---|---|
| pytest | 104 passed | 104 passed |
| node tests | 12 passed | 12 passed |
| ruff check | All checks passed | All checks passed |
| tsc --noEmit | clean | clean |
| next build | — | succeeds (route table intact) |
| npm audit (high) | passes | passes |

Test counts identical before/after — no tests lost. `next build` route table unchanged — no routes affected.

## Remaining Manual Review Items (Tier 2 — require sign-off)

1. **`web/package.json` — direct `lighthouse@^13.4.1` devDependency.** Never imported by code; only `@lhci/cli`'s bundled `lighthouse@12.6.1` is used by `lhci autorun`. Added in commit `9d7302e`. Safe to remove pending sign-off — but left in place because removal touches the dependency manifest and its lockfile churn deserves a human decision.
2. **`app/queries/league_queries.py` — `get_league_teams()`.** Defined and documented in the module docstring, but has zero callers in `app/`, `tests/`, or `scripts/` (verified). Part of the Phase 1 documented query surface, so it may be intentional API surface for a future consumer — recommend removal or explicit deprecation note.
3. **`web/package.json` — no lint script.** Following removal of the broken `next lint` script, the project has no JS lint gate (typecheck + build + tests remain). If a lint gate is wanted, add ESLint 9 flat config with `@next/eslint-plugin-next` and `eslint-plugin-react-hooks` (out of scope for this cleanup).

No Tier 3 findings. No suspected bugs encountered (Section 12: none flagged).

## Final Production-Readiness Score

**96 / 100**

Rubric: 100 baseline; −2 for Tier 2 item #1 (unused `lighthouse` direct dep left pending sign-off); −1 for Tier 2 item #2 (`get_league_teams` dead-but-documented query function); −1 for no JS lint gate (item #3). No behavior change, no test coverage gap, zero artifacts, zero secrets, zero debug leftovers.
