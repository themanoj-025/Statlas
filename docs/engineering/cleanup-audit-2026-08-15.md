# Statlas — Documentation Folder Cleanup & De-LLM-ification Audit (2026-08-15)

## 1. Executive Summary

Scope: full `docs/` tree — `README.md` index, `CONSTITUTION.md`,
`CONTRIBUTING.md`, and the `suite/`, `analytics/`, `api/`, `ai-assistant/`,
`billing/`, `engineering/`, `launch/`, `legal/` topic folders. Statlas is the
**model repo** in the portfolio: it has a single documentation index, a suite
map with cross-links, dated verification logs that honestly record BLOCKED
status instead of fabricating results, and legal/launch docs explicitly gated
on human sign-off. Only fix needed: three verification logs were missing from
the README index (fixed). Governance/legal files flagged but untouched.

## 2. Urgent: Leaked Secrets/Credentials Found

None. Verification logs reference credential *names* (`ANTHROPIC_API_KEY`,
`STRIPE_SECRET_KEY`) and report them as not set — no values are recorded.

## 3. LLM/AI Fingerprints Removed

None found. The `ai-assistant/` folder was given the Section 6 special
scrutiny: its `live-verification-log.md` is a genuine, honest test plan (10
queries with expected tool paths, explicit BLOCKED status) — not a chat
export, prompt log, or scratch pad.

## 4. Structural Changes

- **Fixed** `docs/README.md` index: added the missing `api/`,
  `ai-assistant/`, and `billing/live-verification-log.md` entries. These three
  files were linked from `launch/final-readiness-report.md` but absent from
  the "single home for all documentation" index. Docs-only change.

## 5. Duplicate Content Consolidated

- Three files share the basename `live-verification-log.md` (`ai-assistant/`,
  `api/`, `billing/`). Content is **not** duplicated — each covers a distinct
  subsystem (assistant traces / public API / Stripe billing) with its own
  test plan. Left as-is; noted for awareness only.

## 6. Contradictions Found (manual review, not auto-resolved)

None. Pricing (€7/mo Pro, €49/mo API-Business) is consistent across
`billing/pricing-config.md`, `legal/terms-of-service-draft.md`, and the
verification logs.

## 7. Boilerplate/Template Cruft Removed

None. `suite/DOC-SUITE-MAP.md` is a real cross-link map; no "Coming soon"
stubs anywhere.

## 8. Dead Links Fixed/Removed

None. All internal links resolve (checked with link scanner). The `suite/`
directory link in README is valid on GitHub.

## 9. README / CONTRIBUTING / CONSTITUTION Review

- `docs/README.md` is a genuine index (structure map + "what to read for X"
  guidance) — now complete after this audit's fix.
- `CONSTITUTION.md` (Tier 3) reads formal but project-specific (data-honesty
  rules, §7 definition of done, imagery policy). No template `{{placeholders}}`
  found. Flagged, not edited.
- `CONTRIBUTING.md` (Tier 3) is environment/convention specific. Flagged, not
  edited.

## 10. Security/Privacy Findings

- Legal drafts (`legal/terms-of-service-draft.md`,
  `legal/privacy-policy-draft.md`) are explicitly marked DRAFT — REQUIRES
  LAWYER REVIEW; `[LAWYER]` flags are enumerated. Correctly gated; Tier 3,
  untouched.
- `legal/founder-legal-checklist.md` and `legal/pre-launch-human-actions.md`
  track real founder actions (trademark search, mailbox creation) — genuine
  content, not filler.

## 11. Consistency Fixes Applied

- README index now lists every file in the docs tree (§4).

## 12. Files Modified

- `docs/README.md` (added 3 missing index entries)
- `docs/engineering/cleanup-audit-2026-08-15.md` — added (this report;
  follows the repo's `engineering/cleanup-audit-*` convention)

## 13. Files/Folders Deleted

None.

## 14. Remaining Manual Review Items

1. **Legal drafts (Tier 3)** — ToS + Privacy Policy require lawyer sign-off
   before publication; already tracked in `legal/pre-launch-human-actions.md`.
2. **`CONSTITUTION.md` / `CONTRIBUTING.md` (Tier 3)** — governance weight;
   any change beyond typos needs human sign-off.
3. **Launch gates (Tier 2)** — all three live-verification logs are BLOCKED
   on credentials (Stripe test keys, Anthropic key) and dataset mode
   `fixture-demo`; these are operational gates, not doc defects.

## 15. "Does This Still Look AI-Scaffolded?" Score

**99 / 100** — 100 baseline; −1 for the three same-basename
`live-verification-log.md` files (naming collision, content genuine). No
empty topic folders, no contradictions, no fabricated verification results,
legal/launch docs honestly gated on human review.
