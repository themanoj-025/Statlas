# Pre-launch human actions — tracked checklist

*Status: created 2026-08-14 as part of the Phase 0–2 closeout (Part D). This
document is the single tracked list of items that require a human founder
and/or a licensed lawyer — the AI cannot perform any of these. Each item has an
owner and a status; update status here as items are completed. Nothing below is
auto-resolved.*

> ⚠️ **Nothing in this document is legal advice.** Items marked "lawyer review"
> must be completed by a licensed professional before public launch.

---

## 1. Legal document review (lawyer required)

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1.1 | Lawyer review of `docs/legal/terms-of-service-draft.md` | Founder + lawyer | ⬜ Not Started | Draft is flagged DRAFT — REQUIRES LAWYER REVIEW at top. Must cover accuracy disclaimers, subscription terms, acceptable use, proprietary-metrics clause before public launch. |
| 1.2 | Lawyer review of `docs/legal/privacy-policy-draft.md` | Founder + lawyer | ⬜ Not Started | Draft is flagged DRAFT — REQUIRES LAWYER REVIEW. Stripe is listed as sub-processor; GDPR/UK GDPR position must be confirmed for the founder's jurisdiction. |

## 2. Business registration and domain (founder execution)

Each item from `docs/legal/founder-legal-checklist.md`, tracked individually:

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 2.1 | Research business entity registration in founder's jurisdiction | Founder | ⬜ Not Started | Sole trader vs. Ltd./LLC — tax + liability implications; see founder-legal-checklist.md. |
| 2.2 | Register the business entity | Founder | ⬜ Not Started | Blocked on 2.1. |
| 2.3 | Register domain for chosen name + close variants | Founder | ⬜ Not Started | statlas.com and near-variants (common typos, .com/.net/.co). |
| 2.4 | Set up business email (e.g. data@statlas.com) | Founder | ⬜ Not Started | The scraper User-Agent string already references data@statlas.com — the mailbox must actually exist and be monitored before launch. |
| 2.5 | Trademark search for "Statlas" | Founder (+ trademark counsel if budget allows) | ⬜ Not Started | Before scaled commercial use; see founder-legal-checklist.md. |

## 3. StatsBomb Open Data license re-verification (required before Phase 4 billing)

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 3.1 | Decide StatsBomb §1.2.2 resolution: move shot/pass maps out of the paid tier, obtain a commercial license, or remove the features — then have a lawyer sign off | Founder + lawyer | 🟡 In Progress — research done 2026-08-15; decision + lawyer sign-off pending | LICENSE.pdf re-read in full on 2026-08-15: it is a bespoke **StatsBomb Public Data User Agreement** (8 Sep 2023), NOT CC BY-NC-SA. §1.2.2 bans commercial exploitation of the data **and any analysis derived from it** — this conflicts with the current design where shot/pass maps are gated behind Pro (€7/mo). This is a hard blocker for billing go-live until resolved (sign-off gate). Full analysis: `data-compliance-notes.md` §3. |
| 3.2 | Confirm required attribution UI (StatsBomb logo + source statement) is in place per license terms | Founder + engineer | ⬜ Not Started | Attribution UI exists on maps (Phase 3, e2e-verified) satisfying §1.4; confirm it against the re-verified license text (now documented in `data-compliance-notes.md` §3) before go-live. |

## 4. Data-source operational items (founder/ops, not lawyer)

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 4.1 | Obtain API-Football key for the free-tier budget | Founder | ⬜ Not Started | Scraper implements the 100 req/day budget tracker; needs a real key to run (see production-validation-log.md). |
| 4.2 | Run a credentialed/proxied FBref scrape | Founder/ops | 🔴 Blocked — awaiting founder decision on docs/engineering/fbref-blocker-options.md | FBref returns 403 to the standard pipeline from this build environment; the 2026-08-15 re-diagnosis confirmed a Cloudflare IP-reputation challenge (not UA- or rate-based). The blocker options doc presents 4 paths and requires founder sign-off before any is executed. Blocks `STATLAS_DATASET_MODE=production`. |
| 4.3 | Decide and document entity-level commercial use position on FBref/Understat derived data | Founder + lawyer | ⬜ Not Started | Compliance notes state the mitigation (derived metrics only, never raw table republishing); confirm before launch. |

---

## Status legend

- ⬜ **Not Started** — not begun; owned by the listed human.
- 🟡 **In Progress** — actively being worked by the owner.
- 🔴 **Blocked** — cannot proceed until a named prerequisite (decision/credential/license) resolves.
- ✅ **Complete** — done; date + evidence noted in the Notes column. Only a human may mark a human-owned item complete.

---

## Sign-off gate

Phase 4 (Monetization & Polish) must NOT begin gating features behind billing
until: items 1.1, 1.2, 3.1, 3.2 are complete or explicitly waived in writing by
the founder with the legal risk recorded here. Item 4.2 blocks the
`STATLAS_DATASET_MODE=production` flip — the founder must record a decision on
`docs/engineering/fbref-blocker-options.md` before any option is executed
(2026-08-15 diagnosis: Cloudflare IP-reputation challenge, not UA- or
rate-based).

---

*Updated 2026-08-15 (Final Launch — Part D): status tracking normalized to the
four explicit states above; 4.2 re-marked Blocked with the fresh diagnosis.
No item has been marked Complete — none of these actions has actually
happened yet.*
