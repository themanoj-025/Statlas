# FBref Block — Blocker Options (BLK-01 / RISK-01)

*Created: 2026-08-15 (Final Launch — Part B). This document exists to be read
by the founder and to receive an explicit sign-off. **No option is chosen
here.** Each option is presented with its real researched cost, effort, legal
risk, and effect on the soft launch. The decision is the founder's; a decision
record belongs at the bottom of this file.*

---

## The diagnosis (2026-08-15, live reproduction)

Captured from this build environment's egress IP (Cloudflare PoP `BOM` —
datacenter range):

| Test | Result |
|---|---|
| `GET /en/comps/9/Premier-League-Stats`, project UA | **HTTP 403** — `Server: cloudflare`, `Cf-Mitigated: challenge`, body is the "Just a moment… Enable JavaScript and cookies to continue" challenge page |
| Same URL, generic browser UA (Chrome 126) | **HTTP 403** — identical block |
| `GET /robots.txt` | **HTTP 403** — challenge page; robots.txt content unreadable by automated tools from here |
| Rate of requests | Single request, zero prior traffic → block is **not** rate-limit-based |

**Conclusion: FBref's edge now runs an IP-reputation + interactive JS
challenge (Cloudflare bot management).** The block happens before any request
reaches FBref's origin, so the scraper's rate limiting (10s + jitter, 40%
under FBref's documented ceiling) is never even exercised. The block is a
function of the **egress IP being a datacenter IP**, not of anything the
scraper sends. A browser UA does not help; slowing the scrape does not help
from this IP class.

Full evidence: `docs/analytics/data-compliance-notes.md` §1 (updated 2026-08-15).

**Cross-cutting caveat for every option:** FBref's ToS Clause 5(i) prohibits
automated access without express written permission — a point already flagged
`[LAWYER]` in the compliance notes. Re-verified 2026-08-15 from the live
policy pages: the ToS §5 preamble now *welcomes* sharing data found on
individual pages "whether for commercial or non-commercial purposes" with
credit to SRL, but the data-use page still states you "should not create
websites or tools based on data you scrape from Sports Reference" without
permission, and **custom dataset requests now carry a minimum fee of
$5,000** — a concrete price for the written-permission path. "Technically
unblocked" and "compliant" are different questions; each option below
separates them.

---

## Option 1 — Slower, more conservative scraping (retest with longer delays)

- **What it is:** increase `FBREF_DELAY_SECONDS` well beyond 10s, add
  realistic request headers, retest.
- **Researched assessment:** **diagnostically ineffective from this IP
  class.** The challenge fires before the origin sees any request, so request
  frequency is irrelevant from a datacenter IP. It *might* succeed from a
  residential IP with a real browser (unverifiable from here — would need the
  founder to run it from home), but that still leaves the ToS 5(a) automated-
  access question open.
- **Cost:** €0. **Effort:** low (config change in `sources/base.py`).
- **Risk:** low financial risk; high likelihood of no resolution from this
  environment. Legal position unchanged (still requires written permission).
- **Effect on soft launch:** none — does not unblock production data.

## Option 2 — Paid scraping-compliant proxy / rendering service

- **What it is:** route FBref fetches through a service that renders the JS
  challenge (e.g., ScraperAPI, Zyte API, Bright Data).
- **Researched cost (2026):** roughly **$30–75/month** entry — e.g.,
  ScraperAPI standard tiers ~$29–49/mo (~100k credits at $49/mo per Bright
  Data's published comparison), Zyte API small-volume plans around $29/mo with
  commitment required at higher tiers (Proxyway). Volume for Statlas is low
  (weekly refresh, ≤6–8 pages/source/week), so the entry tier suffices.
- **Effort:** low-moderate — the `StatsSource` interface (Phase 1 B1) makes
  this a transport change in `sources/base.py` (route `fetch_with_retry`
  through the proxy). No schema change.
- **Legal/compliance risk: HIGH — flagged, not glossed over.** A proxy that
  *bypasses* the Cloudflare challenge does not cure FBref ToS Clause 5(a)
  (automated access requires written permission, however routed), and the
  project's own compliance posture (`data-compliance-notes.md`, and the launch
  prompt's constraint "do not attempt to brute-force past a block, which would
  itself violate the Constitution's data-compliance requirements") treats
  challenge-bypass as out of policy. This option only becomes defensible if the
  founder obtains Sports Reference's written permission first.
- **Effect on soft launch:** could unblock production data quickly, but at a
  compliance cost that contradicts the product's core differentiator
  (transparent, defensible data).

## Option 3 — Accelerate the licensed-feed decision (replace FBref as primary per-90 source)

- **What it is:** implement a new `StatsSource` over a licensed feed whose data
  includes the registry's per-90 metrics. The Phase 1 architecture was built
  exactly for this swap (`StatsSource` ABC, `external_ids` per source, alias
  table).
- **Researched options (2026):**
  - **Sportmonks** — self-serve from **~€29/month** (yearly billing ~€34/mo
    per one comparison source), 2,200+ leagues, and a player-statistics
    endpoint covering on-ball/event-derived metrics (shots, passes, crosses,
    tackles, interceptions, clearances, duels, dribbles) with per-90 support
    and minutes. **Gap to verify in a trial:** whether *every* registry metric
    (progressive passes/carries, pressures, xG/xA) is available — xG is
    present; progressive-pass-type and pressure fields must be checked against
    the docs (`docs.sportmonks.com`). Licensed feed → strongest legal footing
    for a commercial derived-metrics product.
  - **API-Football paid** — from **$19/month**, all competitions/endpoints,
    deeper historical archives on paid plans; the free tier (100 req/day) is
    already in the codebase for fixtures. **Gap:** its player-statistics
    granularity is coarser than FBref for some registry metrics, and its terms
    restrict caching/redistribution — re-verify before caching weekly
    snapshots (existing `[LAWYER]` flag in §4 of the compliance notes).
  - **TheStatsAPI** — flat ~**$50/month**, 150 competitions included, 84,000+
    players, 10 years of history (alternative worth a look if Sportmonks'
    metric coverage falls short).
- **Effort:** moderate-high — a new source module, metric mapping from feed
  fields to registry ids, reconciliation against existing players, and a
  methodology-note update if any metric's definition differs from FBref's
  (percentile cohorts stay as defined; only sourcing changes). Estimate: the
  largest single work item of the four options.
- **Risk:** monthly cost commitment; metric-mapping drift risk (mitigated by
  the existing anomaly/coverage gates). Legally the *cleanest* path — this is
  the migration the Constitution always planned for ("licensed feed as revenue
  and user trust justify it").
- **Effect on soft launch:** unblocks production data on a firm legal footing,
  but adds weeks of work before the flip.

## Option 4 — Soft launch on Understat + StatsBomb only; FBref breadth as fast-follow

- **What it is:** flip `STATLAS_DATASET_MODE=production` on the two sources
  already **validated live** (Understat: 562 real player records; StatsBomb:
  7,025 real events — see `docs/analytics/production-validation-log.md`),
  narrow the launch copy to only the leagues/metrics those sources actually
  cover (Understat = Big-5; StatsBomb = the released competitions in
  `data_coverage`), and treat FBref breadth as a post-launch fast-follow.
- **Cost:** €0. **Effort:** low — mode flip + a copy pass over
  `launch-post.md` and the methodology page (league/coverage claims) + updating
  `STATLAS_DATASET_NOTE`. The `data_coverage` matrix already enforces honesty
  mechanically, so the site cannot over-claim once the copy matches.
- **Risk:** narrowed product breadth vs. the current launch-post claims (those
  would need editing — see the pre-flight notes in the final readiness
  report). Understat's own gray-zone legal status (robots `Disallow: /`, no
  express license) remains — it was already accepted as a mitigated risk for
  the MVP, and it does not block derived-metrics publishing the way FBref's
  explicit ToS clause does. API-Football key (item 4.1) is still needed for
  the fixtures layer regardless.
- **Effect on soft launch:** **unblocks the production flip now** — the
  dataset banner stops saying `fixture-demo`, and the Phase 4 Part E live-key
  gates (A1-A3 of the launch prompt) can then run against real data.

---

## Comparison table

| Option | Cost/mo | Effort | Legal posture | Unblocks production flip? | Unblocks soft launch? |
|---|---|---|---|---|---|
| 1. Slower scraping | €0 | Low | Unchanged (still needs written permission) | No (diagnostically ineffective from datacenter IP) | No |
| 2. Proxy/rendering service | ~$30–75 | Low-mod | **Worse** — challenge-bypass conflicts with compliance posture unless written permission obtained | Technically yes | Yes, at compliance cost |
| 3. Licensed feed (Sportmonks / API-Football / TheStatsAPI) | €19–50+ | High | Cleanest — licensed, commercial-safe | Yes (weeks later) | Delayed |
| 4. Understat + StatsBomb only | €0 | Low | As-accepted (Understat gray zone mitigated; StatsBomb non-commercial, maps already gated) | Yes (narrowed claims) | **Yes, now** |

---

## Decision required (founder)

> **BLOCKED — awaiting founder decision.** Pick one option (or a combination,
> e.g., 4 now + 3 as the planned fast-follow). Record the decision below with
> date and rationale. Until a decision is recorded, `STATLAS_DATASET_MODE`
> stays `fixture-demo` and no option is executed.

### Decision record

| Date | Decision | Rationale / notes |
|---|---|---|
| _(blank)_ | _(Option # + scope)_ | _(blank)_ |
