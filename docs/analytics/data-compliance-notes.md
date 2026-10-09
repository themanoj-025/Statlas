# Statlas — Data Source Compliance Notes

*Phase 0 deliverable B1. One compliance note per approved data source, recording what we verified (as of August 2026), the self-imposed limits we commit to, and the mitigation strategy for each. This is a first-draft framework and risk assessment — **none of it is a substitute for a real lawyer.** Items requiring lawyer review before public launch are flagged with `[LAWYER]`.*

*The review outcome for each source is also recorded in the data coverage matrix (Constitution §3) before the source is wired up in Phase 1.*

---

## Core mitigation that applies to every source

No approved source grants Statlas a right to **republish raw data verbatim**. Statlas's product is derived work: percentiles, the Statlas Index, normalized comparisons, and analysis. The universal rules are:

1. **Publish derived/aggregated/normalized metrics only.** Raw scraped tables are never republished verbatim, never offered for download, and never exposed through the API.
2. **Cache aggressively, request minimally.** Every fetch is cached at the pipeline layer; the same page is never fetched twice in a refresh cycle.
3. **Identify the scraper** with a descriptive User-Agent string naming the product and a contact address.
4. **Swappable data-source architecture** (Constitution §4): scrapers sit behind an interface so any source can be replaced by a licensed feed (Wyscout, Opta, Sportmonks) when revenue justifies it. Migration is a planned event, not an emergency.
5. **Anomaly and coverage logging**: a scrape that silently returns half the expected rows is a failure, not a smaller update.

---

## 1. FBref (Sports Reference) — primary per-90 source

**Status: HIGH RISK / best-effort. No commercial redistribution license exists.**

### Access method
Public web pages (league/season stats tables) via HTTP; Cloudflare-protected. FBref publishes **no public API** and states that most of its data is licensed from third parties (Opta) who prohibit raw bulk distribution.

### What we verified (August 2026)
- **Robots.txt:** not reliably fetchable by automated tools (403 response at the server/Cloudflare layer during verification). Sports Reference's published policy pages (`sports-reference.com/bot-traffic.html`, `/429.html`) document their automated-traffic rules instead.
- **Updated 2026-08-15 (BLK-01 re-diagnosis, live):** FBref is now behind a **Cloudflare interactive bot-management challenge**, confirmed from this build environment's egress IP (Cloudflare PoP `BOM` — datacenter range):
  - `GET https://fbref.com/en/comps/9/Premier-League-Stats` → `HTTP 403`, headers `Server: cloudflare`, `Cf-Mitigated: challenge`, body is the "Just a moment… Enable JavaScript and cookies to continue" challenge page.
  - The block is **not User-Agent-based**: a generic browser UA (`Mozilla/5.0 … Chrome/126…`) receives the same 403.
  - It is **not rate-limit-based** (single request, no prior traffic) — it is an edge-level IP-reputation/JS challenge that intercepts requests **before they reach origin**.
  - Even `https://fbref.com/robots.txt` returns the challenge page from this environment, so FBref's current robots.txt content **cannot be read by automated tools here** — a human should re-check it from a normal browser.
  - **Consequence for BLK-01:** slowing the scrape further (Option 1 in `docs/engineering/fbref-blocker-options.md`) will not resolve the block from a datacenter IP — the edge challenges before any request is rate-limited. Options 2-4 in that document are the real paths; the decision is the founder's.
- **Rate limit (documented by Sports Reference):** requests to **FBref and Stathead more often than 10 per minute trigger automated blocking**, with a temporary IP/session block ("jail") of 1 hour up to a full day depending on severity.
- **Terms of Use (Clause 5, sports-reference.com/termsofuse.html):** without express written permission, users may not (a) *"use any automated means to access or use the Site, including scripts, bots, scrapers, data miners, or similar software, in a manner that adversely impacts site performance or access"*; (b) use site data *"to create any database, archive, or other data store that competes with or constitutes a material substitute for the services or data stores offered on the Site or by the Site's Data Providers"*; (c) use site content — including statistics — *"for purposes of training, fine-tuning, prompting, or instructing artificial intelligence models or technologies."*
- **Operational status:** FBref is live and updated daily as of August 2026.
- **RE-VERIFIED 2026-08-15 (fetched live):** `sports-reference.com/termsofuse.html`, `data_use.html`, and `bot-traffic.html` were read in full (the FBref edge blocks automated fetches, but the SR policy pages are browser-accessible). New/changed facts:
  - **ToS §5 preamble — a material softening vs. the earlier reading:** sharing, using, modifying, repackaging, or publishing *data found on individual SRL webpages* is "welcomed, whether for commercial or non-commercial purposes", provided (2) SRL is credited as the source "to the maximum extent possible", and (3) the express restrictions (esp. 5(i), 5(j)) are not violated. The earlier notes' flat "no commercial redistribution license" is now more nuanced: single-page data reuse with credit is affirmatively welcomed; the prohibitions are on automated access that impairs performance (5(i), written permission required), creating a competing/material-substitute database or service (5(j)), and AI-training use of Content (5(k)).
  - **Data-use page (`data_use.html`):** states plainly that you "should not create websites or tools based on data you scrape from Sports Reference or any of our sites" without permission; custom dataset requests now carry a **minimum fee of $5,000** (a concrete number for the written-permission path in `docs/engineering/fbref-blocker-options.md`); and notes facts are not copyrightable, so factual reuse is governed by copyright law, not SRL ownership.
  - **Bot policy (updated 2024-05-29):** rate limit is **10 requests/minute for FBref/Stathead**, 20/min for other SR sites, "regardless of bot type and construction"; violation jails the session up to a day. The project's committed 6/min (40% under) remains compliant; note this ceiling is now irrelevant at the edge because Cloudflare challenges datacenter IPs before origin (v1.1).

### Self-imposed limits (committed, enforced in code)
- **Max 1 request per 10 seconds** (6 requests/minute) with ±2s randomized jitter — deliberately 40% below FBref's documented 10/minute ceiling.
- **Exponential backoff** on any 429/503/block: 1s → 2s → 4s → 8s → 16s → 30s → 60s cap, then abort the run and alert; never hammer through a block.
- **Descriptive User-Agent:** `StatlasAnalytics/0.1 (public football analytics; contact: data@statlas.com)` — never a browser-spoofed UA.
- **Schedule:** all scraping runs during 02:00–06:00 UTC; a hard daily page budget; queueing, never parallelism beyond one worker.
- **Cache:** per-season per-table snapshots cached on disk + DB; identical URLs never refetched within a season.

### Mitigation strategy
Statlas publishes only **derived and normalized metrics** (percentiles, index scores) and never republishes FBref tables verbatim. We do not create a competing database or provide a competing service to FBref's per-90 stats; our product is the derived layer on top. Under ToS Clause 5(b)–(c) this posture is the defensible one, but it is a judgment call, not a guarantee.

`[LAWYER]` Review required before launch: the automated-access clause 5(i) prohibits scraping without written permission even with throttling; the AI-training clause 5(k) means scraped data may **never** be used to train any model (Statlas does not train on FBref data — its AI assistant is grounded on Statlas's own derived database, but a lawyer should confirm that tool-call use of derived percentiles is not within 5(k)); the "material substitute" clause 5(j) is the risk a lawyer should opine on for a derived-metrics product, weighed against the new §5 preamble that welcomes page-level data reuse with credit and the facts-are-not-copyrightable doctrine. The data-use page now prices the permission path: **custom datasets cost a minimum of $5,000**. **Plan: request written permission from Sports Reference; if refused, rely on documented best-effort throttling for non-commercial research data with swappable architecture and a licensed-feed migration plan as the commercial path.**

---

## 2. Understat — xG/xA supplement (Big-5 only)

**Status: NO EXPRESS LICENSE PUBLISHED. Treat as all-rights-reserved; gray zone.**

### Access method
Data is **embedded JSON inside page HTML** (`playersDataObject`, `teamsData`, etc.), parsed from the page source. No public API, no keys.

### What we verified (August 2026)
- **Operational:** understat.com is live, still updated, and the reference for Big-5 xG; the `understatapi` Python client (v0.7.1, Feb 2026) is actively maintained against it.
- **Robots.txt:** `User-agent: *` / `Disallow: /` — the site formally disallows all crawlers.
- **Terms of Service / license:** **none found** on understat.com or its footer. No express grant of any rights.
- **Keys verified for the index:** `xG`, `xA`, `npxG`, `key_passes`, `shots`, `time` (minutes), `games`, `goals`, `assists`, `position`, `player_id`, `player_name` in the per-player season JSON.

### Self-imposed limits (committed)
- **Max 1 request per 5 seconds**; single worker; only the Big-5 league/player pages we actually need for Tier 1 xG/xA.
- **Cache:** one weekly snapshot per league season stored and reused for the whole week — typically ≤ 6–8 requests per weekly refresh.
- **No bulk archiving** beyond the weekly snapshot; no replaying of historical pages unless a specific season gap requires it (reviewed case by case).

### Mitigation strategy
Use Understat only as an xG/xA **supplement** with FBref Opta-xG as fallback and precedence per metric in the registry. Publish derived percentiles only. Treat Understat access as **revocable at any time**: the Tier 1 xG model fallback (FBref Opta xG) and the changelog note described in `methodology.md` §9 are the standing contingency.

`[LAWYER]` The absence of any license, combined with `robots.txt: Disallow: /`, puts automated access in a gray zone even with throttling. **Do not monetize features whose correctness depends on Understat without legal review and a fallback data path.** For MVP research/non-commercial operation this is a documented, mitigated risk; the swappable-architecture rule makes leaving Understat a config change, not a rewrite.

---

## 3. StatsBomb Open Data — event-level data (shot maps, pass maps)

**Status: BESPOKE USER AGREEMENT — NOT Creative Commons. The license bans commercial exploitation of the data AND of any analysis derived from it. Attribution is mandatory.**

### What we verified (August 2026)
- **Repository:** the open-data repo now lives at **github.com/hudl/open-data** (Hudl acquired StatsBomb; the repo moved orgs). Still actively serving competitions.json, matches, events, lineups, and three-sixty data. `LICENSE.pdf` present (165 KB, 5 pages, PDF 1.4).
- **License file — RE-VERIFIED 2026-08-15 (text extracted and read in full):** the PDF is a bespoke **"StatsBomb Public Data User Agreement"** ("StatsBomb Data: User Agreement Standard Terms — last updated **8 September 2023**"), NOT the CC BY-NC-SA 4.0 deed that earlier community references suggested. The earlier compliance note's CC BY-NC-SA attribution was **unverified and is now corrected**. Governing law: England and Wales; StatsBomb Services Ltd, reg. no. 10377735, Bath.
- **README Terms & Conditions (exact):** *"If you publish, share or distribute any research, analysis or insights based on this data, please state the data source as StatsBomb and use our logo, available in our Media Pack."*

### Verified agreement terms that bind Statlas (exact quotes from LICENSE.pdf)
- **§1.2.1** — the User may not: *"edit, distort, distribute, reproduce, sell or in any way provide the data to any external or third party"*;
- **§1.2.2** — the User may not: *"commercially exploit the data or any analysis derived from the use of the Service"* — **this is the load-bearing clause for Statlas**: shot/pass maps are built on this data, and §1.2.2 reaches *derived analysis*, not just raw data;
- **§1.4** — *"The User is required to accredit any publication of analysis formed from StatsBomb Data with the StatsBomb brand logo"* (already implemented as the attribution UI on maps — Phase 3);
- **§2.1** — Service provided via GitHub, *"fully controlled by StatsBomb"*, which may withhold the Service at any time without prior warning;
- **§2.2** — StatsBomb *asks* users to register (name + email) at `statsbomb.com/resource-centre` (an ask, not a hard technical gate);
- **§6.1** — suspension/termination if StatsBomb reasonably believes the data is used otherwise than in accordance with the Agreement;
- **§7** — data is the property of StatsBomb; no exploitation "without the express prior written consent of StatsBomb".

### What this means for Statlas (corrected analysis)
- **Non-commercial research use with attribution: permitted** — this matches the agreement's stated purpose ("aimed to be a research tool").
- **The current paid-tier design conflicts with §1.2.2.** `app/config/pricing.json` gates **shot/pass maps behind Pro (€7/month)** and the API tier exposes data-derived content — that is commercial exploitation of analysis derived from the Service. **This must be resolved before billing go-live** (sign-off gate items 3.1/3.2). Options for the founder + lawyer: (a) move StatsBomb-derived features out of the paid tier (free, research-grade, attributed); (b) obtain a commercial license from StatsBomb/Hudl; (c) remove the features. No option is chosen here.
- **No ShareAlike obligation** (the earlier CC-based concern is moot — the actual agreement has no such clause), but the commercial-exploitation ban is stricter than the CC analysis implied.

### What we commit to
- **Attribution is a UI requirement, not a legal footnote** (Constitution §3): every page rendering StatsBomb-derived content carries the StatsBomb logo, the source statement ("Data by StatsBomb — open data"), the coverage label for the specific competition/season, and a recency line.
- **Coverage honesty:** StatsBomb Open Data covers only specific released competitions/seasons. The data coverage matrix is the arbiter; shot maps are never implied to be universal (Constitution Never-List #8).
- **Non-commercial posture for MVP (currently violated — to be resolved before billing go-live):** StatsBomb-derived features (shot/pass maps) must be research-grade content **outside any commercial/paywalled feature** until a commercial license exists. `app/config/pricing.json` today gates shot/pass maps behind Pro — this contradicts §1.2.2 and is the subject of the decision in `docs/legal/pre-launch-human-actions.md` item 3.1.

`[LAWYER]` (1) The agreement is a bespoke user agreement (8 Sep 2023), already re-read in full 2026-08-15 — the earlier CC BY-NC-SA ShareAlike concern is **moot**; the operative risks are §1.2.2 (commercial exploitation of data AND derived analysis), §1.2.1 (providing the data to any third party — relevant if the public API exposes StatsBomb-derived values), and §7 (no exploitation without express prior written consent). Legal review is required on what the paid tier and API may do with StatsBomb-derived analysis before billing go-live. (2) §1.4 attribution is contract-like and must be honored mechanically — already a UI requirement and implemented on maps. (3) §2.2 asks users to register at statsbomb.com/resource-centre — note the ask in the sync runbook.

---

## 4. API-Football — fixtures / live scores layer only

**Status: FREE TIER EXISTS; terms on caching/redistribution must be re-verified at account creation. Self-imposed limits below keep us inside any reasonable reading.**

### What we verified (August 2026)
- **Free tier:** long-standing published free limit is **100 requests/day** (the api-football.com pricing and terms pages returned 403 to automated fetchers at verification time — Cloudflare-protected — so this figure must be re-confirmed at account creation).
- **Scope for Statlas:** fixtures, standings, and live-score status only — the "live" word in the product is used exclusively for this layer (Constitution §3).
- **Terms:** api-football's published terms have historically restricted caching and redistribution of its data and required attribution. Exact current text: re-verify at signup (`[LAWYER]`/engineering checklist item, Phase 1).

### Self-imposed limits (committed)
- **Ceiling of 80 requests/day** (20% headroom under the 100/day figure) with a daily budget counter that hard-stops the layer.
- **Max 1 request per 2 seconds**; retries with backoff on 429.
- **Cache:** fixture/score payloads cached per league round for the refresh cycle; never stored long-term; never republished in raw form — fixtures are rendered as schedule/live-state UI only.
- **Attribution:** "fixtures and live scores via API-Football" shown on the schedule/live pages that use this layer.

### Mitigation strategy
The fixtures layer is the least sensitive part of the product (it is factual schedule data) and the easiest to replace. If API-Football terms tighten, the same interface swap that protects every other source covers this layer.

`[LAWYER]` Confirm current free-tier limits and the caching/redistribution clauses at signup; if terms prohibit even short-term caching, switch to pass-through rendering or a paid plan before launch.

---

## 5. Cross-cutting risk register

| Risk | Source(s) | Severity | Mitigation | Owner |
|---|---|---|---|---|
| ToS prohibits automated access | FBref | High | Throttle + descriptive UA + written-permission request + derived-only publishing + swappable architecture | Founder + lawyer |
| No express license / robots disallow | Understat | Medium | Minimal weekly fetch, derived-only, FBref fallback, revocable-by-design | Engineering |
| Bespoke agreement bans commercial exploitation of data AND derived analysis (§1.2.2) | StatsBomb | High (commercial) — conflicts with Pro-gated shot/pass maps | Attribution UI (done), coverage matrix, move StatsBomb-derived features out of paid tier or obtain commercial license, §1.2.2 resolution before billing go-live | Founder + lawyer |
| Free-tier limits / caching terms | API-Football | Low | 80/day ceiling, short cache, re-verify at signup | Engineering |
| GDPR: player performance data is personal data | All | High | Legitimate-interest assessment, retention policy, operational DSR path (see `privacy-policy-draft.md`) | Founder + lawyer |

**Required before public launch (not before Phase 1 development):** written permission request to Sports Reference; re-verification of the StatsBomb LICENSE.pdf and API-Football terms; GDPR legitimate-interests assessment sign-off; lawyer review of this document's conclusions.

---

## 6. Versioning

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-08-15 | StatsBomb LICENSE.pdf re-verified (text extracted in full): bespoke "StatsBomb Public Data User Agreement" (8 Sep 2023), NOT CC BY-NC-SA; §1.2.2 bans commercial exploitation of data and derived analysis → conflicts with Pro-gated shot/pass maps. FBref ToS/data-use page re-verified live: §5 welcomes sharing with credit, but data-use page forbids building websites/tools on scraped data without permission; custom dataset requests now have a $5,000 minimum. |
| 1.1 | 2026-08-15 | FBref re-diagnosis (BLK-01): Cloudflare interactive challenge confirmed from datacenter egress IP; block is IP-reputation-based, not UA- or rate-based; robots.txt unreadable by automated tools from this environment. |
| 1.0 | 2026-08-11 | Initial compliance notes for FBref, Understat, StatsBomb Open Data, API-Football; self-imposed limits; lawyer-review flags. Facts verified 2026-08-11; re-verify before Phase 1 wiring and before monetization. |
