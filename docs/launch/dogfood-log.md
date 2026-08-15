# Statlas — Pre-Launch Internal Dogfooding Log (Phase 5 B2)

*Created: 2026-08-14. This log records the internal dogfooding pass run before
any external soft launch. Every entry is a real observation from an actual
session against the running app (API :8000, web :3000) — no synthetic
findings.*

Dogfooding method: real scouting/analysis tasks plus deliberate attempts to
break things — obscure searches, cross-league comparisons, boundary inputs,
missing data, and the assistant's grounding honesty.

---

## Findings

| # | Severity | Area | Finding | Resolution |
|---|---|---|---|---|
| D-01 | info | Operations | The e2e server script and the long-running dev servers serve **stale builds** unless restarted after code changes — a freshly built `/help` and `/about` returned 404 from the old server. Not a product bug, but a real trap for anyone testing against a long-lived server. | Documented here; restart web server (`npx next start`) after builds. No code fix needed. |
| D-02 | info | Search | Obscure searches behave correctly: `zzz` → 0 results, `x` → 8 results (limit respected), accented-name search (`keller` → Andrés Keller) works, whitespace-only query → `[]`. | No action needed. |
| D-03 | info | API validation | Boundary inputs return specific 4xx errors, not 500s: `limit=0` → 422 with `ge=1`, `limit=9999` → 422 with `le=100`, `position=XYZ` → 400, `tier=tier_9` → 400, unknown player slug → 404. | No action needed. |
| D-04 | info | Trend | Trend window is strictly `5`/`10` (422 for `0` and `999`); unknown metric → 400 `unknown metric`. | No action needed. |
| D-05 | info | Compare | Cross-league comparison (`andres-keller` Tier 2 CB vs `theo-andersen` Tier 1 ST) renders 200. | No action needed. |
| D-06 | info | Coverage honesty | Player without event coverage (Kevin De Bruyne) correctly reports `has_event_data: false` with empty competitions — the B4 honest-messaging path is exercised. | No action needed. |
| D-07 | info | Assistant | With `ANTHROPIC_API_KEY` unset the assistant returns an explicit, honest `"not configured on this deployment"` error rather than hallucinating an answer — grounding honesty holds even in the unconfigured state. | No action needed. |
| D-08 | info | Sentence audit | `scripts/audit_sentences.py` scanned all **1,191** players with published percentiles: every data-driven sentence well-formed and within bounds (percentiles 0–100, index 0–100, no fallback copy for qualified players). | Audit script added (Phase 5 A4). |
| D-09 | info | SEO/meta | Real sample of player pages: data-driven meta descriptions, correct OG titles, and OG images returning real images (73–75 KB PNGs). Team pages have data-driven metadata too. | No action needed. |
| D-10 | info | E2E | Full e2e suite (20 tests across 3 breakpoint projects) green after Phase 5 content changes; new Phase 5 spec (7 tests) green. | No action needed. |
| D-11 | note | Methodology | Worked example arithmetic verified independently: Keller's weighted sum (percentiles × CB weights) = **86.87**, matching the live index exactly. | No action needed. |

**Launch-blocking issues found: 0.** No data-accuracy errors, billing bugs, or
broken core flows surfaced during the internal pass.

## Adversarial checks still to run at external launch

The internal pass could not exercise (external prerequisites):

- The AI assistant's grounding under real model responses (requires
  `ANTHROPIC_API_KEY`) — adversarial questions ("what is Haaland's xG this
  season", "who would win X vs Y") must all trace to tool calls.
- Real Stripe checkout in test mode (requires `STRIPE_SECRET_KEY` +
  `STRIPE_WEBHOOK_SECRET`).
- Real concurrent load (soft-launch traffic).

These are tracked in `docs/legal/pre-launch-human-actions.md` and block the
production data flip / billing go-live, per the closeout and Phase 4 logs.
