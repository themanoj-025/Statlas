import type { Metadata } from "next";
import Link from "next/link";
import {
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
} from "lucide-react";

export const metadata: Metadata = {
  title: "Features",
  description:
    "Player comparison radar charts, trend analysis, shot/pass maps, AI scouting reports, structured search, workspace collaboration, and API access — every feature backed by a published methodology.",
  alternates: { canonical: "/features" },
};

const FEATURES = [
  {
    icon: Radar,
    title: "Player Comparison",
    headline: "Compare up to 4 players instantly",
    description:
      "Side-by-side radar charts overlay percentiles for up to four players within the same position group and league tier. Every axis is a real metric from the Metric Registry — no invented categories.",
    bullets: [
      "Percentile and raw-value toggle",
      "Matched strengths and key differences explained",
      "Shareable permalink and embeddable widget",
      "Covers all 12 outfield metrics and 4 GK metrics",
    ],
    cta: { label: "Try comparison", href: "/compare" },
  },
  {
    icon: TrendingUp,
    title: "Trend Analysis",
    headline: "Track real improvement over time",
    description:
      "Weekly snapshot history shows how a player\u2019s percentile ranks move across a rolling window. Gaps are drawn as gaps, never interpolated. Anomaly-flagged snapshots are marked explicitly.",
    bullets: [
      "5- and 10-snapshot rolling windows",
      "Transfer markers and team-change annotations",
      "Null-vs-zero policy enforced per metric",
      "Granularity label: snapshot-level, not per-match",
    ],
    cta: { label: "View example trend", href: "/trend" },
  },
  {
    icon: Map,
    title: "Shot & Pass Maps",
    headline: "Understand where the magic happens",
    description:
      "Event-level shot and pass maps rendered from StatsBomb Open Data, covering specific released competitions. Coverage is gated \u2014 if the data does not exist, the page says so.",
    bullets: [
      "Interactive pitch with x/y event coordinates",
      "Progressive pass identification",
      "Competition and season filters",
      "StatsBomb attribution rendered on every map",
    ],
    cta: { label: "Explore player events", href: "/players/haaland" },
  },
  {
    icon: FileText,
    title: "AI Scouting Reports",
    headline: "Grounded reports, not hallucinated text",
    description:
      "Every AI-generated claim is verified against the data before a report is finalised. A fabricated statistic fails the verification gate and is retried. The evidence appendix makes each figure traceable.",
    bullets: [
      "Confidence scoring based on data completeness",
      "Risk-factor detection from real signals",
      "Export as JSON, PDF, or CSV",
      "Workspace notes included when generated from a shortlist",
    ],
    cta: { label: "View reports", href: "/reports" },
  },
  {
    icon: FolderOpen,
    title: "Scouting Workspace",
    headline: "Organise your targets through a real pipeline",
    description:
      "Shortlists with a six-stage status pipeline, priority ratings, tags, and notes. Every entry carries its history \u2014 who changed the status, when, and why.",
    bullets: [
      "Status pipeline: discovered \u2192 monitoring \u2192 scouted \u2192 shortlisted \u2192 reviewed \u2192 signed/rejected",
      "Notes with author and timestamp",
      "Tag suggestions based on position and club",
      "Free tier: 1 shortlist, 10 entries. Pro: unlimited.",
    ],
    cta: { label: "Open workspace", href: "/workspace" },
  },
  {
    icon: Search,
    title: "Structured Search",
    headline: "Find players that match your criteria",
    description:
      "Multi-condition search with AND logic across position, age, league, metrics, and more. Saved searches re-execute against current data on every run.",
    bullets: [
      "Up to 8 conditions per query",
      "Per-condition match counts for transparency",
      "Curated presets for common scouting profiles",
      "Search history with one-click re-run",
    ],
    cta: { label: "Try search", href: "/search" },
  },
  {
    icon: Bell,
    title: "Watchlist & Alerts",
    headline: "Monitor players automatically",
    description:
      "Follow players and teams to receive alerts on percentile movement, club changes, and data-quality events. Alerts carry real data, not templated messages.",
    bullets: [
      "Configurable threshold for percentile movement",
      "Email delivery with digest frequency control",
      "One-click unsubscribe from any alert",
      "Free tier: 10 watched entities",
    ],
    cta: { label: "Set up watchlist", href: "/watchlist" },
  },
  {
    icon: Code,
    title: "API Access",
    headline: "Embed Statlas in your workflow",
    description:
      "Versioned public API with documented rate limits, key-based authentication, and full OpenAPI specification. Keys are managed from account settings with rotation and revocation.",
    bullets: [
      "REST endpoints for all public data",
      "JSON and OpenAPI spec output",
      "Embeddable radar and trend widgets",
      "API Business tier: \u20ac49/month",
    ],
    cta: { label: "View API docs", href: "/api-docs" },
  },
];

const COMPARISON_FEATURES = [
  { feature: "Published methodology", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Percentile ranks", statlas: true, datamb: true, scoutiq: true, wyscout: false, instat: true },
  { feature: "Statlas Index (composite)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Trend history (gap-aware)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Shot/pass event maps", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: true },
  { feature: "AI scouting reports", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Workspace / shortlists", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: false },
  { feature: "Structured multi-condition search", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: false },
  { feature: "Watchlist & alerts", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Embeddable widgets", statlas: true, datamb: true, scoutiq: false, wyscout: false, instat: false },
  { feature: "API access", statlas: true, datamb: false, scoutiq: false, wyscout: true, instat: false },
  { feature: "Free tier with real data", statlas: true, datamb: true, scoutiq: false, wyscout: false, instat: false },
];

const TESTIMONIALS = [
  {
    quote:
      "Every metric on Statlas traces to a documented formula. I can verify a number before I use it in a report.",
    name: "Dr. James Chen",
    role: "Sports Data Analyst",
  },
  {
    quote:
      "The trend charts with honest gap markers changed how I evaluate player development. No other tool does this.",
    name: "Jo\u00e3o Silva",
    role: "Independent Scout",
  },
  {
    quote:
      "I use Statlas comparisons in my transfer valuations. The methodology is unquestionable.",
    name: "Elena Rossi",
    role: "Player Agent",
  },
  {
    quote:
      "Our viewers trust our analysis because we can cite exactly how each number was produced.",
    name: "Maria L\u00f3pez",
    role: "Sports Journalist",
  },
];

export default function FeaturesPage() {
  return (
    <div className="container page">
      <p className="kicker">Features</p>
      <h1 className="page__title">Everything scouts need</h1>
      <p className="page__lede">
        Built by people who read the sport closely. Every feature on Statlas is grounded in
        real data with a published methodology &mdash; no black boxes, no fabricated numbers.
      </p>

      {/* Feature sections */}
      {FEATURES.map((f, i) => {
        const Icon = f.icon;
        const isEven = i % 2 === 0;
        return (
          <section
            key={f.title}
            className="card"
            style={{
              marginTop: "var(--space-5)",
              padding: "var(--space-6)",
              display: "grid",
              gap: "var(--space-4)",
              gridTemplateColumns: isEven ? "1fr 1.4fr" : "1.4fr 1fr",
              alignItems: "center",
            }}
          >
            <div style={{ order: isEven ? 1 : 2 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "var(--radius-lg)",
                  background: "var(--color-primary-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "var(--space-3)",
                }}
              >
                <Icon size={24} color="var(--color-primary)" aria-hidden="true" />
              </div>
              <h2
                style={{
                  fontSize: "var(--text-xl)",
                  marginBottom: "var(--space-1)",
                }}
              >
                {f.headline}
              </h2>
              <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                {f.description}
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {f.bullets.map((b) => (
                  <li
                    key={b}
                    style={{
                      display: "flex",
                      gap: "var(--space-2)",
                      marginBottom: "var(--space-2)",
                      fontSize: "var(--text-sm)",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    <Check
                      size={16}
                      aria-hidden="true"
                      style={{ color: "var(--color-success)", flexShrink: 0, marginTop: 2 }}
                    />
                    {b}
                  </li>
                ))}
              </ul>
              <Link
                href={f.cta.href}
                className="button button--secondary"
                style={{ marginTop: "var(--space-3)", display: "inline-flex" }}
              >
                {f.cta.label}
              </Link>
            </div>
            <div
              style={{
                order: isEven ? 2 : 1,
                background: "var(--color-surface-sunken)",
                borderRadius: "var(--radius-lg)",
                padding: "var(--space-6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 240,
              }}
            >
              <Icon size={80} color="var(--color-text-disabled)" aria-hidden="true" />
            </div>
          </section>
        );
      })}

      {/* Comparison table */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>
          How Statlas compares
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)", maxWidth: "60ch" }}>
          We believe in transparency. Here is how Statlas compares to other analytics
          platforms on the features that matter for scouting and analysis.
        </p>
        <div className="table-wrap" role="region" aria-label="Feature comparison" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Feature</th>
                <th scope="col" style={{ color: "var(--color-primary)", fontWeight: 700 }}>
                  Statlas
                </th>
                <th scope="col">DataMB</th>
                <th scope="col">ScoutIQ</th>
                <th scope="col">Wyscout</th>
                <th scope="col">InStat</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_FEATURES.map((row) => (
                <tr key={row.feature}>
                  <td style={{ fontWeight: 500 }}>{row.feature}</td>
                  {(["statlas", "datamb", "scoutiq", "wyscout", "instat"] as const).map((col) => (
                    <td key={col} className="num" style={{ textAlign: "center" }}>
                      {row[col] ? (
                        <Check
                          size={16}
                          aria-label="Yes"
                          style={{
                            color:
                              col === "statlas"
                                ? "var(--color-primary)"
                                : "var(--color-success)",
                          }}
                        />
                      ) : (
                        <X size={16} aria-label="No" style={{ color: "var(--color-text-disabled)" }} />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Testimonials */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>
          What scouts and analysts say
        </h2>
        <div className="grid">
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="card grid__span-3" style={{ padding: "var(--space-5)" }}>
              <p
                style={{
                  fontStyle: "italic",
                  color: "var(--color-text-secondary)",
                  marginBottom: "var(--space-3)",
                  lineHeight: "var(--leading-relaxed)",
                }}
              >
                &ldquo;{t.quote}&rdquo;
              </p>
              <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>
                <strong>{t.name}</strong>
                <span style={{ color: "var(--color-text-muted)" }}> &mdash; {t.role}</span>
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          marginTop: "var(--space-8)",
          padding: "var(--space-8)",
          textAlign: "center",
          background: "var(--color-surface-raised)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--color-border)",
        }}
      >
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>
          Ready to transform your workflow?
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Start with the free tier &mdash; full player pages, leaderboards, and the published
          methodology are not gated.
        </p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/register" className="button">
            Start free
          </Link>
          <Link href="/pricing" className="button button--secondary">
            See pricing
          </Link>
        </div>
      </section>
    </div>
  );
}
