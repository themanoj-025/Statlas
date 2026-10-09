# Statlas — Final Launch Readiness Report

*Created: 2026-08-15 (Final Launch Execution — Part E). Consolidated status of
the last mile: live-key gates, the FBref blocker, soft-launch execution
support, and human-owned items. Written to the launch prompt's hard
constraints: **no fabricated verification results, no public posting, no
human item marked complete without a human doing it, no unilateral choice on
the FBref decision.***

---

## 1. What was completed in this session

### Part A — Live-key verification gates → all three BLOCKED, honestly

No live credential exists in this environment (checked `2026-08-15`:
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ANTHROPIC_API_KEY`, and the
API-Football key are all unset). Per the prompt, each gate is recorded as
**BLOCKED** with the exact credential required — **no simulated results**:

| Gate | Log | Status |
|---|---|---|
| Stripe test-mode checkout | [`docs/billing/live-verification-log.md`](../billing/live-verification-log.md) | BLOCKED — Stripe test keys + webhook secret + Pro price id |
| AI assistant live queries | [`docs/ai-assistant/live-verification-log.md`](../ai-assistant/live-verification-log.md) | BLOCKED — `ANTHROPIC_API_KEY` |
| Public API live calls | [`docs/api/live-verification-log.md`](../api/live-verification-log.md) | BLOCKED — API-Business subscription requires Stripe keys first |

Each log contains a **ready-to-run test plan** (T1–T6 for billing; the exact
10-query grounding audit for the assistant; every endpoint + 429/401/403
checks for the API) that executes verbatim the moment the credentials land.
**Dependency flag:** all three gates must run after the production data flip —
as-is they would validate against `fixture-demo` data, which the prompt
explicitly warns against.

### Part B — FBref blocker (BLK-01) diagnosed and options documented

- **Live re-diagnosis (2026-08-15):** FBref is behind a **Cloudflare
  IP-reputation + interactive JS challenge** (`Cf-Mitigated: challenge`,
  `Server: cloudflare`). A generic browser UA gets the same 403; `robots.txt`
  is also challenged; the block fires before any request reaches origin, so
  rate-limiting is irrelevant from this datacenter egress IP (Cloudflare PoP
  `BOM`). Evidence recorded in [`docs/analytics/data-compliance-notes.md`](../analytics/data-compliance-notes.md) §1 (version 1.1).
- **Options document:** [`docs/engineering/fbref-blocker-options.md`](../engineering/fbref-blocker-options.md) presents four options with
  researched 2026 costs — (1) slower scraping (€0, diagnostically ineffective
  from datacenter IPs), (2) proxy/rendering service (~$30–75/mo, technically
  unblocks but conflicts with the compliance posture and does not cure FBref
  ToS clause 5(a)), (3) licensed feed (Sportmonks ~€29/mo, API-Football
  from $19/mo, TheStatsAPI ~$50/mo — legally cleanest, highest effort), (4)
  soft launch on Understat + StatsBomb only (€0, unblocks the production flip
  now with narrowed copy). **No option was chosen — the decision record at the
  bottom of that document is blank and awaits founder sign-off.**

### Part C — Soft-launch execution support

- **Pre-flight of launch materials (C1):** every feature claim in
  [`launch-post.md`](launch-post.md) was checked against the shipped product —
  radar/compare/permalink, trend charts, coverage-gated shot/pass maps, embed
  widgets, grounded assistant, report-a-data-error, and the €7/month Pro price
  (matches `app/config/pricing.json`). Findings in §3 below: **three items
  make the post not-shippable as written** (dataset mode, domain, mailboxes).
- **Triage tooling (C2):** [`scripts/feedback.py`](../../scripts/feedback.py) —
  structured JSONL intake + resolution + daily rollup against the go/no-go
  criteria, with a strict mode that exits 1 on any accuracy-SLA breach
  (>24h). **Tested:** add/resolve/summary paths pass, strict-mode SLA breach
  correctly detected (exit 1), help screens render, output is ASCII-safe on
  Windows consoles. Entries live in `docs/launch/feedback-entries.jsonl`
  (currently empty — window opens when the post ships).
- **Go/no-go template (C3):** [`docs/launch/go-no-go-template.md`](go-no-go-template.md) —
  blank, fixed criteria, nothing pre-filled.
- **Human handoff (C4):** see §4 below.

### Part D — Human/legal action items

[`docs/legal/pre-launch-human-actions.md`](../legal/pre-launch-human-actions.md)
updated with the explicit four-state legend (Not Started / In Progress /
Blocked / Complete). Item 4.2 re-marked **Blocked** (Cloudflare diagnosis +
options doc link). **No item was marked Complete — none of these actions has
actually happened.**

---

## 2. What remains BLOCKED — and on whom

| # | Item | Blocked on | Owner |
|---|---|---|---|
| 1 | Stripe test-mode checkout + webhook verification (T1–T6) | Stripe test keys, webhook secret, Pro price id | Founder |
| 2 | 10 live assistant queries (grounding audit) | `ANTHROPIC_API_KEY` | Founder |
| 3 | Public API live calls (endpoints + 429/401/403) | API-Business subscription → Stripe keys (item 1) | Founder |
| 4 | FBref resolution | **Decision** between the 4 options in `docs/engineering/fbref-blocker-options.md` | Founder |
| 5 | `STATLAS_DATASET_MODE=production` flip | Item 4 (or narrowed-sources variant of Option 4), then re-run sentence audit + LHCI on real data | Founder + Eng |
| 6 | Posting the launch announcement | Human action — posting is not delegated | Founder |
| 7 | Feedback channels live (`data@statlas.com`, `feedback@statlas.com`) | Mailbox setup (pre-launch item 2.4) | Founder |
| 8 | Domain (`statlas.com`) referenced in the post | Domain registration (item 2.3) | Founder |
| 9 | Legal: ToS + privacy lawyer review (1.1, 1.2) | Lawyer engagement | Founder + lawyer |
| 10 | StatsBomb license re-verification (3.1, 3.2) | License re-read + attribution confirmation | Founder + lawyer |
| 11 | Business registration, email, trademark (2.1, 2.2, 2.5) | Founder execution | Founder |
| 12 | API-Football key (4.1); FBref/Understat commercial-use position (4.3) | Key signup; lawyer position | Founder |

---

## 3. Pre-flight findings — the launch post as written is not shippable

1. **Dataset mode is `fixture-demo` (blocking).** The post says *"the data
   pipeline is real (per-90 stats…)"* but does not disclose that the live site
   currently serves **labeled fixture data**. Posting the announcement as-is
   while the mode is `fixture-demo` would overclaim — a direct Constitution
   violation, and exactly the kind of thing the target audience (skeptical
   analysts) would catch. Two honest paths, both founder-decided: **(a) flip
   to production on narrowed sources first** (FBref options → Option 4), or
   **(b) edit the post to disclose the demo-data state.** The post must not
   ship unchanged.
2. **Domain unregistered.** The post links `statlas.com`; item 2.3 is Not
   Started. The URL in the announcement must resolve.
3. **Mailboxes unconfirmed.** The report-a-data-error `mailto:` and the
   `feedback@statlas.com` channel reference mailboxes that are Not Started
   (item 2.4). The scraper User-Agent also names `data@statlas.com`. A launch
   whose feedback channel is a dead mailbox would destroy the trust the
   methodology-first framing exists to build.

Verified clean: all feature claims, €7/month pricing, report-a-data-error
mechanism (component + e2e green), and the methodology worked example
(reproducible index 86.87 — dogfood D-11).

---

## 4. Human handoff — what only the founder can do (C4)

1. **Decide the FBref path** — record a choice in
   `docs/engineering/fbref-blocker-options.md` (decision record at bottom).
   Consideration, not a recommendation-as-decision: Option 4 unblocks fastest
   and honestly; Option 3 is the clean long-term path; Option 1 is
   diagnostically dead from datacenter IPs; Option 2 conflicts with the
   compliance posture without written permission.
2. **Resolve the pre-flight blockers** — register the domain, create the two
   mailboxes, and either flip production data (after the FBref decision) or
   edit the launch post to disclose the demo-data state.
3. **Set the live credentials** — Stripe test keys + webhook secret +
   Anthropic key; then run the three verification logs (test plans are
   written and waiting). Do not skip these: they are the Phase 4 Part E gates.
4. **Post the launch** — publish `docs/launch/launch-post.md` to the target
   communities named in `soft-launch-plan.md` (analytics Twitter/X,
   r/footballanalysis + r/soccer, analytics Discords); record date/URL in the
   triage log's execution record; monitor the mailbox daily.
5. **Run the window** — log feedback with `python scripts/feedback.py add …`
   as it arrives; run `summary` daily; reply to every accuracy report within
   24h and changelog the fixes.
6. **Decide go/no-go at day 14** — fill in `go-no-go-template.md` with real
   data and record the decision.
7. **Work the legal list** — lawyer review of ToS/privacy, StatsBomb license
   re-verification, entity/domain/trademark (items 1.1–4.3 in
   `docs/legal/pre-launch-human-actions.md`). Nothing here can be done by an
   AI.

---

## 5. Recommendation

**Not yet ready to post the launch — and the evidence says so plainly.**

- The product is built and its Phase 5 Part A–C deliverables are genuine and
  verified (content, audit, changelog, cadence, dogfooding with zero
  blockers).
- But the launch post cannot ship as written: the site serves fixture data
  while the post implies production data, the domain it links is not
  registered, and its feedback mailboxes are not confirmed live.
- None of the Phase 4 Part E live-key gates have passed (all BLOCKED on
  missing credentials) — and per the prompt's own dependency rule they must
  run against production data anyway.

**Sequenced path to "go":**
1. Founder decides the FBref option (documented, not chosen here).
2. Production flip on the decided scope → re-run sentence audit (1,191
   players) + LHCI + e2e on real payloads.
3. Domain + mailboxes live; launch copy re-verified against the flipped
   dataset.
4. Live-key gates pass (billing → assistant → API), evidence appended to the
   three logs.
5. Post → 14-day window → triage (`scripts/feedback.py`) → go/no-go template
   filled with real data.

Until steps 1–4 are real, the honest status is **BLOCKED on founder actions**
— not because the product is unbuilt, but because launching it now would
violate the same honesty rules the product is built on.

---

*Owner: founder (solo). Evidence links: the four logs above, the options doc,
the triage tooling, and `docs/legal/pre-launch-human-actions.md`.*
