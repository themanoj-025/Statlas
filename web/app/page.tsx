import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Radar,
  TrendingUp,
  Map,
  FileText,
  FolderOpen,
  Search,
  Bell,
  Code,
  Check,
  X,
  ChevronRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatNumber, percentileBand } from "@/lib/format";

export const metadata: Metadata = {
  title: "Statlas — football analytics that shows its work",
  description:
    "Per-90 statistics, percentile ranks and the Statlas Index for football players across Tier 1–3 leagues, with a fully published methodology. No black box, no fabricated numbers.",
  openGraph: {
    title: "Statlas — football analytics that shows its work",
    description:
      "The only football analytics platform that publishes its methodology. Compare players, analyse trends, and trust the numbers.",
    type: "website",
  },
};

/* -------------------------------------------------------------------------- */
/*  Pricing tiers (static data — no fabrication, matches /pricing page)       */
/* -------------------------------------------------------------------------- */
const PRICING_TIERS = [
  {
    name: "Free",
    price: "\u20ac0",
    period: "/month",
    description: "Get started with essentials",
    cta: "Sign up free",
    ctaHref: "/register",
    highlighted: false,
    features: [
      { text: "Unlimited player searches", included: true },
      { text: "Radar comparisons (2 players)", included: true },
      { text: "5 saved shortlists", included: true },
      { text: "10 saved searches", included: true },
      { text: "1 report/month", included: true },
      { text: "Team workspace", included: false },
      { text: "API access", included: false },
    ],
  },
  {
    name: "Pro",
    price: "\u20ac7",
    period: "/month",
    description: "For professional scouts",
    cta: "Start 14-day free trial",
    ctaHref: "/register?plan=pro",
    highlighted: true,
    badge: "Most popular",
    features: [
      { text: "Everything in Free", included: true },
      { text: "Radar comparisons (4 players)", included: true },
      { text: "Unlimited shortlists", included: true },
      { text: "10 reports/month", included: true },
      { text: "Team workspace (5 members)", included: true },
      { text: "Shot/pass maps", included: true },
      { text: "Priority support", included: true },
    ],
  },
  {
    name: "Business",
    price: "\u20ac49",
    period: "/month",
    description: "For media and agencies",
    cta: "Contact sales",
    ctaHref: "/contact",
    highlighted: false,
    features: [
      { text: "Everything in Pro", included: true },
      { text: "Unlimited team members", included: true },
      { text: "API access (1,000 req/day)", included: true },
      { text: "Custom integrations", included: true },
      { text: "Dedicated support", included: true },
      { text: "SSO/SAML", included: true },
      { text: "SLA: 99.95% uptime", included: true },
    ],
  },
];

const USE_CASES = [
  { title: "For Scouts", quote: "Statlas cuts my research time in half. I trust every number.", href: "/use-cases/scout" },
  { title: "For Agents", quote: "I use Statlas to negotiate better contracts with data-backed valuations.", href: "/use-cases/agent" },
  { title: "For Analysts", quote: "Finally, stats with the methods published. I can audit everything.", href: "/use-cases/analyst" },
  { title: "For Media", quote: "Our viewers trust our analysis because we explain every stat.", href: "/use-cases/media" },
  { title: "For Fans", quote: "I finally understand what percentiles mean. This is how stats should be presented.", href: "/use-cases/fan" },
];

const FEATURES = [
  { icon: Radar, title: "Player Comparison", desc: "Compare up to 4 players side-by-side on radar charts. See strengths and weaknesses instantly.", href: "/compare" },
  { icon: TrendingUp, title: "Trend Analysis", desc: "Weekly snapshots show real improvement. Filled gaps are honest, never interpolated.", href: "/trend" },
  { icon: Map, title: "Shot & Pass Maps", desc: "Every shot, pass, and progressive action mapped. Understand where the magic happens.", href: "/data-coverage" },
  { icon: FileText, title: "AI Reports", desc: "Grounded scouting reports verified against real data. No fabricated stats.", href: "/reports" },
  { icon: FolderOpen, title: "Workspace", desc: "Shortlists, notes, tags, and a six-stage status pipeline for real decision processes.", href: "/workspace" },
  { icon: Search, title: "Structured Search", desc: "Multi-condition search across position, age, league, and 12+ metrics.", href: "/search" },
  { icon: Bell, title: "Watchlist & Alerts", desc: "Follow players and get notified on percentile movement and club changes.", href: "/watchlist" },
  { icon: Code, title: "API Access", desc: "Versioned REST API with OpenAPI spec. Embed charts, export data, build integrations.", href: "/api-docs" },
];

export default async function HomePage() {
  const [meta, leaderboard, leagues, positions] = await Promise.all([
    api.meta(),
    api.leaderboard({ metric: "si_index", tier: "tier_1", position: "ST", season: "2025-26", limit: 10 }),
    api.leagues(),
    api.positions(),
  ]);

  const inCoverage = leagues.filter((l) => l.has_fbref_coverage);
  const tier1Leagues = inCoverage.filter((l) => l.tier === "tier_1");
  const season = leaderboard.entries[0]?.snapshot_date?.slice(0, 10) ?? "";
  const qualCount = positions.reduce((sum, g) => sum + (g.qualifying_counts?.tier_1 ?? 0), 0);

  return (
    <>
      {/* ─── HERO SECTION ─── */}
      <section
        style={{
          background: "linear-gradient(135deg, var(--pitch-800) 0%, var(--pitch-600) 100%)",
          color: "var(--color-text-inverse)",
          padding: "var(--space-10) 0 var(--space-9)",
        }}
      >
        <div className="container" style={{ textAlign: "center" }}>
          <p
            style={{
              fontSize: "var(--text-xs)",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color: "var(--pitch-200)",
              marginBottom: "var(--space-3)",
            }}
          >
            Football analytics
          </p>
          <h1
            style={{
              fontSize: "var(--text-4xl)",
              color: "#fff",
              maxWidth: "20ch",
              margin: "0 auto var(--space-4)",
            }}
          >
            Football analytics that shows its work
          </h1>
          <p
            style={{
              fontSize: "var(--text-lg)",
              color: "var(--pitch-100)",
              maxWidth: "50ch",
              margin: "0 auto var(--space-5)",
              lineHeight: "var(--leading-normal)",
            }}
          >
            Per-90 statistics, percentile ranks, and the Statlas Index — every metric
            traces to a published formula. No black box, no fabricated numbers.
          </p>
          <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              href="/register"
              className="button"
              style={{ background: "#fff", color: "var(--pitch-700)", fontSize: "var(--text-base)", padding: "var(--space-3) var(--space-5)" }}
            >
              Start free trial
            </Link>
            <Link
              href="/methodology"
              className="button"
              style={{ background: "transparent", border: "1px solid var(--pitch-300)", color: "#fff", fontSize: "var(--text-base)", padding: "var(--space-3) var(--space-5)" }}
            >
              View methodology
            </Link>
          </div>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--pitch-200)", marginTop: "var(--space-4)" }}>
            No credit card required · Cancel anytime
          </p>
        </div>
      </section>

      <div className="container page">
        {/* ─── SOCIAL PROOF METRICS ─── */}
        <div
          className="grid"
          style={{
            padding: "var(--space-5) 0",
            borderBottom: "1px solid var(--color-divider)",
            marginBottom: "var(--space-6)",
          }}
        >
          {[
            { value: `${meta.metrics ? Object.keys(meta.metrics).length : 16}`, label: "tracked metrics" },
            { value: "3", label: "league tiers" },
            { value: `${qualCount.toLocaleString()}`, label: "qualifying players (Tier 1)" },
            { value: "Weekly", label: "data refresh cadence" },
          ].map((m) => (
            <div key={m.label} style={{ textAlign: "center" }}>
              <div className="num" style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--color-primary)" }}>
                {m.value}
              </div>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>{m.label}</div>
            </div>
          ))}
        </div>

        {/* ─── PROBLEM SECTION ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="grid" style={{ alignItems: "center" }}>
            <div>
              <h2 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-3)" }}>
                The problem with football analytics
              </h2>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {[
                  "Stats are scattered across sources with different definitions",
                  "Proprietary tools cost thousands per year with hidden formulas",
                  "Composite scores are trade secrets — you have to trust what vendors tell you",
                  "Missing data is interpolated silently, hiding gaps from users",
                ].map((item) => (
                  <li
                    key={item}
                    style={{
                      padding: "var(--space-3) 0",
                      borderBottom: "1px solid var(--color-divider)",
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-secondary)",
                      display: "flex",
                      gap: "var(--space-2)",
                    }}
                  >
                    <X size={16} style={{ color: "var(--color-danger)", flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div
              style={{
                background: "var(--color-surface-sunken)",
                borderRadius: "var(--radius-lg)",
                padding: "var(--space-6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "var(--text-4xl)", marginBottom: "var(--space-2)" }}>?</div>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", margin: 0 }}>
                  How is this number calculated?
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── SOLUTION SECTION ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <h2 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-4)", textAlign: "center" }}>
            The Statlas approach
          </h2>
          <div className="grid">
            {[
              {
                icon: Code,
                title: "Every number has a formula",
                desc: "Our metrics are published as code in a registry. Click any stat on the site to see how it is calculated.",
                cta: { label: "Read the methodology", href: "/methodology" },
              },
              {
                icon: Search,
                title: "Missing data is marked, not guessed",
                desc: "We never interpolate. Gaps are gaps. You decide what to do with them.",
                cta: { label: "Check data coverage", href: "/data-coverage" },
              },
              {
                icon: Radar,
                title: "Works where you work",
                desc: "Embed charts, export reports, integrate via API. Your data, your way.",
                cta: { label: "View API docs", href: "/api-docs" },
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.title} className="card grid__span-4" style={{ padding: "var(--space-5)" }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "var(--radius-md)",
                      background: "var(--color-primary-muted)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginBottom: "var(--space-3)",
                    }}
                  >
                    <Icon size={20} color="var(--color-primary)" aria-hidden="true" />
                  </div>
                  <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-2)" }}>{s.title}</h3>
                  <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                    {s.desc}
                  </p>
                  <Link href={s.cta.href} style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>
                    {s.cta.label} <ChevronRight size={14} aria-hidden="true" style={{ verticalAlign: "middle" }} />
                  </Link>
                </div>
              );
            })}
          </div>
        </section>

        {/* ─── FEATURES OVERVIEW ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Features</h2>
            <Link href="/features" style={{ fontSize: "var(--text-sm)" }}>
              All features →
            </Link>
          </div>
          <div className="grid">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <Link key={f.title} href={f.href} className="card grid__span-3" style={{ textDecoration: "none", color: "var(--color-text-primary)" }}>
                  <Icon size={20} color="var(--color-primary)" aria-hidden="true" style={{ marginBottom: "var(--space-2)" }} />
                  <h3 style={{ fontSize: "var(--text-sm)", marginBottom: "var(--space-1)" }}>{f.title}</h3>
                  <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", margin: 0 }}>{f.desc}</p>
                </Link>
              );
            })}
          </div>
        </section>

        {/* ─── USE CASES ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Who uses Statlas</h2>
          </div>
          <div className="grid">
            {USE_CASES.map((uc) => (
              <Link key={uc.title} href={uc.href} className="card grid__span-3" style={{ textDecoration: "none", color: "var(--color-text-primary)" }}>
                <h3 style={{ fontSize: "var(--text-sm)", fontWeight: 700, marginBottom: "var(--space-2)" }}>{uc.title}</h3>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontStyle: "italic", margin: 0 }}>
                  &ldquo;{uc.quote}&rdquo;
                </p>
              </Link>
            ))}
          </div>
        </section>

        {/* ─── PRICING PREVIEW ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Simple pricing</h2>
            <Link href="/pricing" style={{ fontSize: "var(--text-sm)" }}>
              Full pricing →
            </Link>
          </div>
          <div className="grid">
            {PRICING_TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`card grid__span-4`}
                style={{
                  padding: "var(--space-5)",
                  borderColor: tier.highlighted ? "var(--color-primary)" : undefined,
                  position: "relative",
                }}
              >
                {tier.badge && (
                  <span
                    className="chip chip--primary"
                    style={{ position: "absolute", top: "calc(-1 * var(--space-2))", right: "var(--space-3)" }}
                  >
                    {tier.badge}
                  </span>
                )}
                <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-1)" }}>{tier.name}</h3>
                <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-1)", marginBottom: "var(--space-2)" }}>
                  <span className="num" style={{ fontSize: "var(--text-2xl)", fontWeight: 700 }}>{tier.price}</span>
                  <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>{tier.period}</span>
                </div>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                  {tier.description}
                </p>
                <Link href={tier.ctaHref} className={`button ${tier.highlighted ? "" : "button--secondary"}`} style={{ width: "100%", marginBottom: "var(--space-4)" }}>
                  {tier.cta}
                </Link>
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {tier.features.map((f) => (
                    <li key={f.text} style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-start", marginBottom: "var(--space-2)", fontSize: "var(--text-sm)" }}>
                      {f.included ? (
                        <Check size={14} style={{ color: "var(--color-success)", flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
                      ) : (
                        <X size={14} style={{ color: "var(--color-text-disabled)", flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
                      )}
                      <span style={{ color: f.included ? "var(--color-text-primary)" : "var(--color-text-muted)" }}>{f.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* ─── LIVE LEADERBOARD (real data) ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Tier 1 Strikers — Statlas Index {season}</h2>
            <Link href="/positions" style={{ fontSize: "var(--text-sm)" }}>
              All leaderboards →
            </Link>
          </div>
          <div className="card card--flush">
            <div className="table-wrap" style={{ border: "none", borderRadius: 0 }}>
              <table className="table" aria-label="Tier 1 strikers ranked by the Statlas Index">
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">Player</th>
                    <th scope="col">Club</th>
                    <th scope="col">Index</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.entries.map((entry, index) => (
                    <tr key={entry.player_id}>
                      <td className="num">{index + 1}</td>
                      <td>
                        {entry.slug ? <Link href={`/players/${entry.slug}`}>{entry.name}</Link> : entry.name}
                      </td>
                      <td>{entry.club ?? "\u2014"}</td>
                      <td className="num" style={{ color: percentileBand(entry.value), fontWeight: 600 }}>
                        {formatNumber(entry.value, 1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ─── POSITION GROUPS ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Position groups</h2>
            <Link href="/positions" style={{ fontSize: "var(--text-sm)" }}>
              All groups →
            </Link>
          </div>
          <div className="grid">
            {positions.map((group) => (
              <Link
                key={group.code}
                href={`/leagues/premier-league/positions/${group.code.toLowerCase()}`}
                className="position-card grid__span-3"
              >
                <span className="position-card__code">{group.code}</span>
                <span className="position-card__name" style={{ display: "block" }}>
                  {group.plural}
                </span>
                <span className="position-card__meta">
                  {(group.qualifying_counts?.tier_1 ?? 0).toLocaleString()} qualifying in Tier 1
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* ─── LEAGUES IN COVERAGE ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <div className="section-head">
            <h2>Leagues in coverage</h2>
            <Link href="/data-coverage" style={{ fontSize: "var(--text-sm)" }}>
              Data coverage →
            </Link>
          </div>
          <div className="grid">
            {tier1Leagues.map((league) => (
              <Link key={league.slug} href={`/leagues/${league.slug}/index`} className="position-card grid__span-3">
                <span className="position-card__name" style={{ display: "block" }}>
                  {league.name}
                </span>
                <span className="position-card__meta">
                  {league.tier_label} · {league.seasons_available[0] ?? "\u2014"}
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* ─── DATA SOURCES / INTEGRATIONS ─── */}
        <section style={{ marginBottom: "var(--space-8)" }}>
          <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)", textAlign: "center" }}>
            Data sources
          </h2>
          <div style={{ display: "flex", justifyContent: "center", gap: "var(--space-6)", flexWrap: "wrap" }}>
            {["FBref", "Understat", "StatsBomb Open Data"].map((source) => (
              <div
                key={source}
                style={{
                  padding: "var(--space-3) var(--space-5)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "var(--text-sm)",
                  fontWeight: 500,
                  color: "var(--color-text-secondary)",
                }}
              >
                {source}
              </div>
            ))}
          </div>
        </section>

        {/* ─── CTA SECTION ─── */}
        <section
          style={{
            padding: "var(--space-8)",
            textAlign: "center",
            background: "var(--color-surface-raised)",
            borderRadius: "var(--radius-xl)",
            border: "1px solid var(--color-border)",
            marginBottom: "var(--space-4)",
          }}
        >
          <h2 style={{ fontSize: "var(--text-2xl)", marginBottom: "var(--space-2)" }}>
            Get started for free
          </h2>
          <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)", maxWidth: "50ch", margin: "0 auto var(--space-4)" }}>
            Full player pages, leaderboards, and the published methodology are not gated.
            No credit card required.
          </p>
          <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/register" className="button" style={{ fontSize: "var(--text-base)", padding: "var(--space-3) var(--space-5)" }}>
              Start free trial
            </Link>
            <Link href="/methodology" className="button button--secondary" style={{ fontSize: "var(--text-base)", padding: "var(--space-3) var(--space-5)" }}>
              View methodology
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
