# Soft Launch — Go/No-Go Decision Template

*Created: 2026-08-15 (Final Launch — Part C3). Fill in at the end of the
14-day soft-launch window with real data only. The criteria below are fixed
**before** the window opens (soft-launch-plan.md §B5) and are not renegotiated
at the end. Do not pre-fill with hoped-for outcomes; leave every cell blank
until the evidence exists. A `no-go` is not a failure — it is the soft launch
working as designed.*

---

## Window

- **Opened:** (date the first launch post shipped — see feedback-triage-log.md §Execution record)
- **Closes:** (opened + 14 days)

## Criterion 1 — No unresolved critical data-accuracy bugs after 14 days

"Critical" = a number that is wrong for a real player (not a methodology
clarification). All critical items fixed **and changelogged**.

- Unresolved critical items on day 14: ____
- Critical items fixed during window: ____ (list FB-ids from `scripts/feedback.py summary` / triage log)
- Each fix has a dated changelog entry? ☐ yes ☐ no — link: ____
- **Pass?** ☐

## Criterion 2 — Positive qualitative sentiment from ≥ 60% of engaged users

"Engaged" = users who sent feedback or used the product more than once.

- Engaged users: ____
- Positive / neutral / negative counts: ____ / ____ / ____
- Basis: (mailbox review summary, thread replies, Discord reactions — attach notes)
- **Pass?** ☐

## Criterion 3 — No major infrastructure incidents

No sustained outage > 30 minutes under real concurrent usage; no data-loss or
corruption event.

- Incidents logged (with duration): ____
- Worst outage / data event: ____
- **Pass?** ☐

## Criterion 4 — At least one organic free → Pro conversion

Proof the value proposition AND the checkout flow work in the real world, not
just Stripe test mode.

- Organic conversions during window: ____
- Evidence: (Stripe dashboard record — real card, not test mode)
- **Pass?** ☐

---

## Decision

- **GO → wider public launch** ☐
- **NO-GO → extend the window by a defined period, with the failing
  criterion(s) named as the explicit focus** ☐

## If NO-GO — named focus for the extension

- Failing criterion: ____
- Extension window: ____
- What changes in the next window to address it: ____

## Notes

- (Anything the numbers don't capture: notable feedback themes, user stories,
  incidents worth remembering.)

---

*Decided by: founder (solo) · Date: ____ · Evidence files:
`docs/launch/feedback-triage-log.md`, `docs/launch/feedback-entries.jsonl`
(machine-readable, via `scripts/feedback.py summary`).*
