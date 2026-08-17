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
