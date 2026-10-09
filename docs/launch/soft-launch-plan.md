# Statlas — Soft Launch Plan

*Created: 2026-08-14 (Phase 5 — Part B). Owner: founder (solo).*

This document defines the soft launch *before* it happens: who is invited, what
the launch is for, how feedback is collected and triaged, and — most
importantly — the pre-defined criteria used to decide go/no-go for the wider
public launch. The execution record lives in
[`feedback-triage-log.md`](feedback-triage-log.md) and the announcement text in
[`launch-post.md`](launch-post.md).

---

## B1 — Audience, goal, and scope

### Target audience

Independent football analytics communities — the people who already use FBref,
Understat, and DataMB and will evaluate Statlas critically against what they
know:

- Football analytics Twitter/X (the accounts that post scouting threads and
  percentile charts)
- Relevant subreddits (r/soccer, r/footballanalysis, r/scouting)
- Analytics-focused Discord servers (scouting/analytics communities)

This audience is chosen deliberately: they are the most likely to (a) find a
data-accuracy error, (b) check the methodology against real numbers, and (c)
care about transparent methodology as a differentiator. Their skepticism is
the point — it is the test this launch exists to pass.

### Explicit goal (written down before launching)

**Primary goal: find data-accuracy bugs.** The dataset has only ever been
exercised by its own build team. A skeptical analyst who knows a specific
player's real numbers is the strongest test available short of a licensed
feed. Data-accuracy reports are triaged first and fixed same/next-day.

**Secondary goals (in priority order):**
1. Validate the pricing/value proposition — will the free tier's genuinely
   useful surface convert anyone to Pro organically?
2. Stress-test infrastructure under real concurrent load.
3. Validate the methodology page's worked example is checkable by a stranger.

### Bounded scope

- **Not an open announcement.** Invites go to a targeted set of people /
  communities, not a general public post.
- **Target: 25–50 engaged initial users** (invites + community posts in the
  named communities only).
- **Duration: 2 weeks**, then a go/no-go decision against B5 criteria. If
  criteria are not met, the soft launch extends rather than proceeding to a
  wider launch prematurely.

---

## B3 — Launch execution

### The announcement

The full post text is in [`launch-post.md`](launch-post.md). Framing rules (per
the Constitution's honesty stance):

- Describes what Statlas actually does — no overclaiming maturity.
- States plainly it is new and early-stage.
- **Leads with the methodology page** — transparent methodology is the core
  differentiator, and a technical audience responds to being shown the formula.
- **Explicitly invites critical feedback and data-accuracy scrutiny** — this
  framing turns skepticism into engagement rather than adversarial pushback.

### Feedback channels

Two channels, deliberately separate:

| Channel | Purpose | Mechanism |
|---|---|---|
| **Data-accuracy reports** | Structured bug reports per page | "Report a data error" link on every player/team page → pre-filled email to data@statlas.com (implemented Phase 5 A5) |
| **Open-ended feedback** | Qualitative input: pricing, UX, feature requests, general sentiment | Dedicated feedback mailbox `feedback@statlas.com` + optional community thread (Discord/Reddit thread where the launch post lives) |

The separation matters: a data-accuracy report has a defined SLA (B4); open
feedback is read in weekly triage. Mixing them would bury accuracy reports
under general commentary.

---

## B4 — Feedback triage process

### Categories

Every incoming item is tagged with exactly one category:

| Category | Definition | SLA during soft launch |
|---|---|---|
| **data-accuracy** | A number on the site does not match reality or the published methodology | Same/next-day fix; response to the reporter within 24h |
| **bug** | A page, flow, or component misbehaves (not a data value) | Same/next-day if critical-path; otherwise within the week |
| **feature-request** | A capability Statlas does not have | Logged, triaged weekly, no immediate action |
| **pricing** | Value/price feedback | Logged, folded into go/no-go assessment |
| **sentiment** | General impression | Logged; informs positioning |

### Response discipline

- Every data-accuracy report gets a reply, even when the report turns out to be
  a user misunderstanding (the reply then explains the metric).
- Fixes made in response to feedback are logged as **dated changelog entries**
  (Part C2) — the soft-launch bug-fixing process is itself visible,
  trust-building content for the community that tested the product.
- Before/after is tracked in the triage log: what was found, what was fixed,
  how long resolution took.

---

## B5 — Success criteria and go/no-go

These criteria are fixed **before** the launch window opens and are not
renegotiated at the end. The decision document is written at the end of the
window in `feedback-triage-log.md` §"Go/no-go decision".

### Criteria (all must pass for go)

- [ ] **No unresolved critical data-accuracy bugs** after 14 days. "Critical"
      = a number that is wrong for a real player (not a methodology
      clarification). All critical items fixed and changelogged.
- [ ] **Positive qualitative sentiment from ≥ 60% of engaged users.**
      "Engaged" = users who sent feedback or used the product more than once.
- [ ] **No major infrastructure incidents.** No sustained outage > 30 minutes
      under real concurrent usage; no data-loss or corruption event.
- [ ] **At least one organic free → Pro conversion.** Proof the value
      proposition AND the checkout flow both work in the real world, not just
      in Stripe test mode.

### Go → wider public launch

Proceed to the go-to-market plan (SEO, embed widgets at scale, non-English
locales, B2B evaluation) as the next body of work.

### No-go → extend

If any criterion fails, the soft launch extends by another defined window with
the failing criterion named as the explicit focus. A no-go is not a failure —
it is the process working as designed (the whole point of a *soft* launch is
that a no-go is cheap and informative).

---

## Related documents

| Document | Relationship |
|---|---|
| [`launch-post.md`](launch-post.md) | The announcement text (B3) |
| [`feedback-triage-log.md`](feedback-triage-log.md) | Execution record: what was sent, where, what came back, resolution (B4) + go/no-go decision (B5) |
| [`dogfood-log.md`](dogfood-log.md) | Pre-launch internal dogfooding record (B2) |
| `docs/analytics/production-validation-log.md` | The data-validation evidence trail this launch assumes |
| `docs/legal/pre-launch-human-actions.md` | Human action items (Stripe keys, FBref credential, StatsBomb license re-check) that gate launch |
