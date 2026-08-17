import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Changelog",
  description: "Dated changelog for Statlas — started during development, maintained going forward.",
  alternates: { canonical: "/changelog" },
};

type Entry = {
  date: string;
  phase: string;
  items: string[];
};

const ENTRIES: Entry[] = [
  {
    date: "2026-08-18",
    phase: "Phase 10 — watchlist & alerts",
    items: [
      "Follow players and teams (both are first-class watch entities) and Statlas comes to you instead of waiting for you to come back. Alert triggers are precisely defined and boundary-tested, with the exact thresholds documented and deployment-tunable (docs/product/alert-trigger-definitions.md): a percentile jump of 15+ points between consecutive published weekly snapshots (inclusive, both snapshots above the 900-minute qualification floor, watched metrics only — a broad watch covers the position's metric set, or you can follow specific metrics), a club change between snapshots (fires once per transfer, never per subsequent week), the first qualifying snapshot of a new season (fires once per season), and Statlas-specific data-honesty alerts — event-data coverage newly gained, or an unresolved ingestion anomaly flagged on the player's snapshot. Non-triggers are documented too: trivial shifts, movement in metrics you didn't choose to watch, and re-detection of the same underlying event are all silent by design.",
      "The detection job is a step in the existing weekly refresh (after publish, idempotent like the rest of the pipeline): it batch-loads every watched entity's snapshot pair in a handful of queries (not N per watch — the scaling strategy is documented in docs/engineering/watch-detection-scaling-notes.md), evaluates all four trigger types against the documented thresholds, and writes watch_alerts whose detail fields hold only real snapshot/coverage/anomaly values — an alert saying '62nd to 81st percentile' is checkable against the actual percentile_snapshots rows.",
      "Notification delivery respects preferences absolutely (docs/product/notification-delivery.md): email_enabled, per-trigger-type opt-in/out, and digest frequency (immediate / daily / weekly) are all honored — an opted-out type or channel genuinely produces no email, tested as rigorously as an authorization check. Digest users get ONE batched email per period, never one per alert (the anti-noise principle). Every email carries real, specific copy populated from the alert's detail data (never 'something changed'), is branded with the design tokens, and includes a genuine one-click unsubscribe — RFC 8058 List-Unsubscribe header plus a signed, sessionless link that sets email_enabled=false; token rotation invalidates old links. Provider: Resend, key-gated exactly like the assistant and reports — unset key means an honest not-configured state, never a silent failure.",
      "In-app notification center: an accessible bell in the signed-in header (unread badge, screen-reader announcement of the count, fully keyboard-navigable dropdown) with read/dismiss actions and a link from every alert to the relevant player/team profile. The /watchlist page lists followed entities with recent alerts and unfollow, and clicking an alert opens a detail view showing the full real supporting data (before/after percentile values and snapshot dates) — the claim stays checkable everywhere. Notification settings live at /watchlist/settings (email on/off, per-type toggles, digest frequency) and link straight from the watchlist.",
      "Follow buttons are integrated on player and team profile pages (consistent with Add-to-Shortlist / Generate Report): signed-out users get an honest 'Sign in to follow' link, free tier gets 10 watched entities with the same specific upsell wording as Phases 7/8/9, Pro is unlimited. Unfollowing deletes the watch but never the alert history (audit bias).",
      "36 new unit/API tests (289 total): threshold boundary cases (just-below silent, just-above and exactly-at alert, inclusive), qualification-floor behavior, idempotency (re-running detection creates nothing), club-change fires-once across three snapshots, new-season once-per-season, coverage-gained and source-anomaly alerts, watched-metrics refinement, preference compliance (opted-out type produces no email — the critical test), digest batching (two alerts → one email), digest-day logic, sessionless unsubscribe (valid/invalid signatures), cross-user 404s, free-tier cap, and the e2e seed fixture being hard-disabled outside e2e.",
    ],
  },
  {
    date: "2026-08-17",
    phase: "Phase 9 — AI scouting reports",
    items: [
      "Grounded report generation that is architecturally incapable of shipping an unverified claim: the pipeline deterministically gathers every number from the existing query layer (percentiles, raw stats, Phase 6 comparables with their explanations, the Phase 3 trend, and your own workspace notes when generated from a shortlist entry) into a verified context corpus, a narrator (LLM via Anthropic, key-gated) may only produce prose from that corpus, and a hard post-generation gate re-checks every number and metric name against it. A fabricated statistic fails verification, the report is retried once with the mismatch fed back, and a second failure stores the report as 'needs review' — held, never silently shipped. Every verification outcome is logged for the Phase 4 accuracy-monitoring loop (docs/product/scouting-reports.md).",
      "Confidence is computed, not vibes: a deterministic scoring function over sample size (minutes vs. the 900-minute qualification threshold), data completeness (fraction of the position's metric set present), and data recency (days since the snapshot) — the level and the factor values that produced it are stated in the report. Risk factors derive only from real signals (sample size, single-season coverage, event-data availability, age vs. the documented position peak range) plus an explicit statement that injury history, attitude and off-field factors are outside what Statlas data can support — silence never implies completeness.",
      "Reports are stored per-user (like shortlists and saved searches) with the same 404-not-403 ownership rule, labelled with their data snapshot date and offering 'regenerate with current data' (which creates a fresh verified report — the stored one is never silently mutated). Pro-only with a SEPARATE monthly allowance from the chat quota, so generating a report never quietly drains your assistant messages; the cap produces the same honest upsell wording as Phases 7/8.",
      "Three export formats derived from the single verified report object: JSON (verbatim, evidence appendix included — the canonical format), a branded PDF applying the design tokens with a native radar chart and a data-snapshot footer (uncompressed content so text stays extractable for screen readers), and CSV (statistical profile + comparable players — the tabular surfaces; the export UI documents what CSV necessarily omits). The in-app viewer renders every section with an expandable evidence appendix tracing each claim to its source call, so a skeptical scout can inspect the sourcing without downloading anything.",
      "Entry points match the established pattern: Generate Report on the player profile header and on every shortlist entry (with the workspace context included and clearly labelled as your own input), plus a Reports page in the signed-in header linking to history. The generation UI shows the real pipeline steps (Gathering player data… Analyzing comparables… Verifying claims…) rather than a black-box spinner, and surfaces the honest needs-review and not-configured states instead of hiding them.",
      "32 new unit/API tests (252 total) including the verification-rejection test — a deliberately fabricated statistic is demonstrably caught by the gate — plus confidence scoring, risk-factor rules, pipeline integration, workspace-context inclusion/omission, cross-user 404s, quota caps, and all three export formats.",
    ],
  },
  {
    date: "2026-08-17",
    phase: "Phase 8 — structured search",
    items: [
      "Multi-condition query builder at /search: combine up to 8 conditions (percentile thresholds relative to position group × league tier, raw minutes, age, position, tier) under AND-only logic — OR/grouped logic is a documented future enhancement (docs/product/query-builder-scope.md), not a half-built feature. Percentile and raw conditions are visually distinct in the builder, every metric comes from the same Metric Registry used by the Radar tool and similarity explanations (no second naming convention), and a debounced live preview shows how restrictive the query is before you commit. Every result row shows the real values behind each condition — the why-it-matched is checkable, never a bare list.",
      "Correctness by construction: query translation is covered by hand-calculated tests (multi-condition AND, percentile+raw mixing, lte/between), the 900-minute qualification floor is ALWAYS applied even when the query has no minutes condition (a builder query can never surface unqualified players), and a player missing data for any condition metric is excluded — a player cannot satisfy a condition on data that doesn't exist for them. Empty-result queries return per-condition pass counts naming the most restrictive condition so the UI can say 'try lowering X' instead of a bare no-results.",
      "Persistence with the Phase 7 ownership model: saved searches (Free tier capped at 5 with the same honest upsell wording as shortlists; Pro unlimited), automatic search history (newest 50 per user, logged on every real run — never the debounced preview), and re-running a saved search always executes against CURRENT data with the weekly-refresh caveat stated in the UI — results are never silently served stale.",
      "Nine curated presets with real, validated query definitions and one-line scouting rationales (High-potential young progressors, Ball-winning defensive midfielders, Undervalued creative wide players, …) — each verified to return a real non-empty result set against the current population by scripts/validate_search_presets.py (9/9 OK).",
      "Results integrate with the Phase 7 workspace: Add to Shortlist on every result row plus a bulk 'Add all to shortlist' action (one deliberate step, then a real shortlist selector), so the flow is build a query → review candidates → track the promising ones.",
      "35 new unit/API tests (220 total) including the translation-correctness matrix, the floor, missing-metric exclusion, cross-user 404s on saved searches and history, history retention, and the free-tier cap; axe green on the builder, and full keyboard operability of the condition rows.",
    ],
  },
  {
    date: "2026-08-17",
    phase: "Phase 7 — scouting workspace",
    items: [
      "Persistent per-user scouting workspace: shortlists (multiple, named), players added from any profile/leaderboard/similar-players surface, free-form tags with autocomplete from your own vocabulary, timestamped notes (relative + absolute dates), priorities, and a defined status pipeline: discovered → monitoring → scouted → shortlisted → reviewed, plus rejected and signed as terminal-but-reversible states. Forward moves may skip stages; backward moves are allowed; a rejected player can only be reconsidered via Monitoring; Signed is terminal. Every change writes a status_history row — the full audit trail (who, from, to, when, why) is queryable, so 'how long has this been in Monitoring?' is answerable (docs/product/scouting-pipeline.md).",
      "Real authorization, not UI hiding: every workspace query verifies ownership and returns 404 (never 403) for another user's shortlist or entry, so a shortlist's existence never leaks. Soft delete for entries and shortlists (notes, tags and history preserved); a player can sit in many shortlists but never twice in one. Free tier gets a genuine taste — 1 shortlist, 10 players each — with an explicit, honest upsell message at the cap; Pro is unlimited.",
      "Workspace UI: /workspace overview (cards with per-status breakdowns, create-new-shortlist, remove) and /workspace/[id] detail (status filter, deliberate status-change control with optional reason note — never an accidental one-click flip, priority select, tag chips with your-own-tags autocomplete, expandable notes with timestamps, add/remove). All states implemented: loading skeletons, empty-shortlist onboarding, signed-out prompt, retry-capable error. Every status/priority chip pairs colour with a text label; axe green on both pages.",
      "Add to Shortlist is integrated where players appear: the player profile header, every leaderboard row, and every similar-players result. The component is lazy (zero requests until first click), handles multiple shortlists with a real selector plus inline create, marks already-saved players, and routes signed-out users to sign-in and capped free users to the honest Pro upsell.",
      "43 new unit/API tests (185 total): pipeline transitions valid + explicitly invalid, cross-user 404s on read and write, duplicate-add rejection, soft-delete audit preservation, free-tier caps, own-only tag suggestions, and a multi-step status-history audit scenario.",
    ],
  },
  {
    date: "2026-08-17",
    phase: "Phase 6 — explainable similarity",
    items: [
      "Every similar-players result now carries a real explanation computed from the same percentile vectors that produced the score — never a template sentence unconnected to the numbers. Matched strengths are the metrics that contributed most to the cosine score where both players rank at or above the 70th percentile within 20 points; key differences are the largest percentile-point gaps (at least 25 points) with the stronger player stated. The decomposition reuses the dot product and norms already computed for ranking, so the explanation cannot diverge from the headline number (docs/analytics/similarity-explanation-method.md).",
      "Explanation UI on the player profile: each similar player expands to show matched strengths with up-indicators and key differences with the stronger player named, each with real percentile values (e.g. 'both rank highly in Progressive carries per 90 — 88th vs 85th percentile'). Honest states included: if no metric has a meaningful gap the UI says the profiles are very similar across every measured metric; metrics missing a published percentile for either player are excluded from score and explanation and listed with the reason; loading skeleton, empty, and retry-capable error states all defined. Icons carry accompanying text and every colour is a semantic token (WCAG AA, axe green).",
      "Similarity explanation covered by 11 hand-calculated unit tests (matched-strength ranking, key-difference direction, boundary gaps, missing-metric exclusion, no-meaningful-differences edge case, contribution-sum consistency) plus integration tests through the query layer; methodology page gained a 'Similar players — how the explanation works' section with the exact thresholds; API reference updated; a verification script (scripts/verify_similarity_explanations.py) checks internal consistency across 10+ real player pairs.",
    ],
  },
  {
    date: "2026-08-14",
    phase: "Phase 5 — launch readiness",
    items: [
      "Methodology page now carries a full worked example from the current dataset — a real player's twelve percentile × weight contributions summing exactly to their published Statlas Index (86.87 for Andrés Keller), so the formula is checkable by hand rather than taken on faith.",
      "About page added (what Statlas is, what it deliberately is not, and the honest fact that it is a solo project). Pricing page now answers the real objections in an FAQ — data freshness, cancellation and end-of-period access, what happens to saved comparisons/embeds/exports on downgrade (they persist), payment-failure grace period, and the API tier.",
      "Help & FAQ page added: how percentiles are calculated, the three concrete reasons a player may be missing (below the 900-minute threshold, outside coverage, or held by the anomaly gate), billing and cancellation, null-vs-zero policy, and how to report a data error.",
      "Every player and team page now has a Report a data error link — a pre-filled email naming the page, so accuracy reports arrive with context and are never a dead mailbox.",
      "Data-driven sentence audit: scripts/audit_sentences.py now checks every data-driven sentence across the full dataset (1,191 players with published percentiles — all clean) for grammar, out-of-range percentiles/index, and qualified players wrongly getting fallback copy.",
      "Soft-launch package: plan (audience, explicit goal, bounded scope), launch post, dogfooding log (internal pass found zero launch-blocking issues), feedback triage log with pre-defined go/no-go criteria, and the process for turning soft-launch fixes into dated changelog entries.",
    ],
  },
  {
    date: "2026-08-14",
    phase: "Phase 4 — monetization & polish",
    items: [
      "Accounts and auth: email+password registration/login with hashed passwords (PBKDF2) and server-side sessions whose tokens are stored only as hashes.",
      "Stripe subscriptions (test-mode, key-gated): hosted Checkout for Free → Pro, immediate optimistic access grant on success (webhook-confirmed shortly after), a subscriptions table as the single source of truth for access, one reusable has_pro_access() gate used everywhere, and a billing portal for payment methods / invoices / cancellation. Cancellation keeps Pro access until the end of the paid period.",
      "Webhook handling with the failure modes treated as first-class: every event is signature-verified, idempotent (event_id unique key — replays are recorded, never double-processed), and fully logged; invoice.payment_failed enters a grace period with clear on-site messaging instead of an abrupt cutoff; subscription.deleted revokes access with a defined downgrade path (saved work persists, volume limits revert).",
      "Grounded AI assistant: function-calling only, over the real query layer (percentiles, leaderboard, trend, similar players, coverage). The system prompt forbids answering any numeric claim that did not come from a tool call; every response with a stat shows the actual query and parameters in an expandable data-used section. Per-user quota (hard cap, reset date stated) with rate limiting and logging for grounding violations.",
      "Public API (v1): key-based auth with hashed key storage (plaintext shown once at creation), rotation and revocation from the account dashboard, tiered rate limits with X-RateLimit-* headers, and documentation rendered from the live OpenAPI spec at /api-docs.",
      "Hardening: axe automated on the new billing/assistant pages in CI (caught and fixed a real contrast violation on the pricing Recommended chip — 4.47:1 to 6.23:1), Lighthouse urls added for the new pages, and a security review confirming no Stripe secrets or key-generation logic client-side, webhook signature rejection tested, and key hashing verified.",
    ],
  },
  {
    date: "2026-08-14",
    phase: "Closeout — Phases 0–2 hardening",
    items: [
      "Live pipeline validation (Part A): ran the real Understat and StatsBomb Open Data syncs against their live endpoints. Found and fixed three real-world drift bugs the fixture-only suite hid: an infinite loop in the scraper backoff scheduler (would exhaust memory on repeated failures), Understat removing the embedded playersDataObject payload (data now served from the POST /main/getPlayersStats/ endpoint — scraper falls back to it), and competitions.json changing shape from nested seasons to a flat list. Real Understat validation pulled 562 live player records; real StatsBomb sync wrote 7,025 events + accurate coverage rows. FBref is bot-blocked (403) from this environment; documented in the validation log — a credentialed/proxied FBref run remains before production flip.",
      "Tier-completeness gate (Part C1): percentiles now key source precedence by (player, source, league tier) — the same-season cross-tier transfer collision is fixed with a migration + regression test; the §1.4 gate withholds a tier's percentiles until every league in the tier is ingested, with the coverage matrix as arbiter.",
      "Timezone policy (Part C2): documented (UTC in the backend, conversion only at display), fixed all naive date.today() call sites, DTZ lint rule now enforced.",
      "PostgreSQL parity (Part C3): full pipeline + API verified against a real Postgres 17 container — found and fixed the native_enum=False VARCHAR-cast bug that broke ORM inserts against real enum columns; parity notes in docs/engineering/postgres-parity-notes.md.",
      "Test suite cleanup (Part C4): blind pytest.raises(Exception) replaced with specific types; all deferred ruff findings (SIM103/SIM102/SIM114, UP037) resolved with real simplifications.",
      "Security CI (Part C5): gitleaks secret scan, pip-audit, npm audit enforced; Dependabot config; infra plan (staging + backup strategy) documented.",
      "Quality gates automated (Part B): Playwright e2e for radar generation + leaderboard search/filter; axe-core audits on the four Phase 2 pages failing on any violation; automated no-horizontal-overflow checks at 375/768/1440px in light + dark themes; Lighthouse CI enforcing LCP < 2.5s (measured 572–720ms). Fixed three real layout bugs these checks exposed.",
      "Constitution §7 Definition-of-Done checklist closed: every item completed or explicitly re-scoped (checkout e2e moved to Phase 4 with billing; FBref live scrape blocked from this environment, tracked).",
      "Known limitation recorded: the pipeline still serves the labeled fixture dataset (STATLAS_DATASET_MODE=fixture-demo); the production flip requires a credentialed FBref scrape + API-Football key, tracked in docs/analytics/production-validation-log.md.",
    ],
  },
  {
    date: "2026-08-13",
    phase: "Phase 3 — trends, maps, sharing",
    items: [
      "Trend charts: snapshot-history line/area charts per player × metric with percentile/raw toggle, configurable rolling window (5/10 snapshots), multi-player + multi-metric overlay, and honest gap handling — a missing snapshot renders a dashed break, never a false interpolation. Transfer events (team_id changes) and flagged snapshots (unresolved anomalies) are annotated from real data.",
      "Trend backend: get_player_trend reads the versioned stat_snapshots table (the Phase 1 append-only design is what makes this feature possible), resolves per-date values with the registry's source precedence, and reports snapshot granularity explicitly — never per-match precision.",
      "Shot & pass maps, coverage-gated: the /events API and map components render ONLY where data_coverage confirms the competition/season AND match events exist for the player. Outcomes use shape + colour (never colour alone); xG scales shot size; passes are directional arrows with completion/progressive filters; every map has a data-table toggle for screen readers and the mandatory StatsBomb attribution.",
      "Player-event link step: match_events resolve to players by exact normalized name (ambiguous names stay NULL and are logged — never a fuzzy guess). The match_events.extra column now carries shot xG, pass end coordinates/type/recipient, and the raw event player name.",
      "Honest unavailability messaging: players without event coverage see a factual note listing exactly which competitions Statlas holds event data for — no grayed-out coming-soon that implies universal coverage.",
      "Sharing layer: stable permalinks encode the exact chart state (players + metrics + window + mode) for Compare and Trend; dynamic Open Graph images render the real chart with real data (pure SVG builders + next/og); responsive, lazy-loaded iframe embeds with Powered-by-Statlas attribution; a sharing panel with copy-link/copy-embed/social intents and proper feedback states.",
      "Seed upgrades: the dev dataset now runs 7 weekly scrape dates with deterministic per-player drift, one deliberately missing snapshot (gap demo) and one mid-season transfer (annotation demo), plus synthetic StatsBomb event data for Haaland/Salah under real coverage rows.",
      "Known limitation recorded: trend granularity is snapshot-level (weekly scrapes), not per-match — per-match trends require match-level ingestion, which Phase 1 did not build. Flagged explicitly in the trend API response and chart copy.",
    ],
  },
  {
    date: "2026-08-12",
    phase: "Phase 2 — first user-facing surface",
    items: [
      "Radar tool: SVG radar with percentile/raw per-90 toggle, 1–4 player overlay, per-axis tooltips, skeleton/empty/error states, keyboard-accessible vertices, and a data-table alternative.",
      "Player profiles (server-rendered): data-driven sentence generator, key-stat summary, similar players (cosine similarity over percentile vectors, basis stated), dynamic title/description/OG image, JSON-LD Person.",
      "Team profiles: roster table, squad-average radar, JSON-LD SportsTeam, honest logo placeholder.",
      "Leaderboards: sortable, filterable, paginated tables consuming the Phase 1 query layer via the new versioned API (FastAPI /api/v1).",
      "League per-90 stats, position-group pages, compare tool with permalink form, methodology, data coverage, pricing, changelog, and legal pages.",
      "Information architecture locked in site-map.md and navigation-and-flows.md.",
      "Development dataset: `python scripts/seed_dev_db.py` builds data/dev.db through the real pipeline (fixture parsers + labeled synthetic leagues). The API reports dataset_mode=fixture-demo and the UI shows a banner until a real refresh + STATLAS_DATASET_MODE=production.",
      "Known limitation recorded: compute/percentiles.py keys source precedence per (player, source) without a tier dimension, so a same-season cross-tier transfer would collide on percentile unique keys (fail-loudly today). Out of Phase 1 scope; scheduled with the §1.4 completeness gate.",
    ],
  },
  {
    date: "2026-08-11",
    phase: "Phase 1 — data pipeline",
    items: [
      "Schema (PostgreSQL DDL + ORM mirror) with append-only snapshots, idempotent natural keys, anomaly gate, and data_coverage matrix.",
      "Sources: FBref, Understat, StatsBomb Open Data, API-Football behind the StatsSource interface with compliance rate limits.",
      "Reconciliation with alias store and human-review queue; anomaly detection; fractional-rank percentiles; Statlas Index with verifier.",
      "Weekly refresh orchestration with publish gate; documented deviation: the tier-completeness gate (§1.4) is not enforced in Phase 1.",
    ],
  },
  {
    date: "2026-08-10",
    phase: "Phase 0 — design & governance",
    items: [
      "Master Constitution (v1.1), design system, tokens.css, component-state specs, methodology, percentile rules, data compliance notes, legal drafts.",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Changelog</p>
      <h1 className="page__title">Changelog</h1>
      <p className="page__lede">
        Dated, honest entries — started during development, maintained going forward. Nothing here
        is backfilled.
      </p>

      {ENTRIES.map((entry) => (
        <section key={entry.date} style={{ marginBottom: "var(--space-6)" }}>
          <h2 style={{ fontSize: "var(--text-lg)" }}>
            {entry.date} <span className="chip chip--primary">{entry.phase}</span>
          </h2>
          <ul style={{ margin: 0, paddingLeft: "var(--space-4)" }}>
            {entry.items.map((item) => (
              <li key={item} style={{ fontSize: "var(--text-sm)", marginBottom: "var(--space-2)" }}>
                {item}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
