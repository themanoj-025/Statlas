import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Interactive Showcase",
  description:
    "Experience Statlas features without registering. Pre-loaded data with real players, working radar comparisons, and trend charts.",
  alternates: { canonical: "/showcase" },
};

const DEMO_FEATURES = [
  {
    title: "Player Profiles",
    desc: "View full player profiles with percentiles, the Statlas Index, and data-driven sentences.",
    link: "/players/haaland",
    linkLabel: "View Haaland's profile",
  },
  {
    title: "Radar Comparisons",
    desc: "Compare up to 4 players side-by-side. See matched strengths and key differences explained.",
    link: "/compare",
    linkLabel: "Try comparison tool",
  },
  {
    title: "Trend Analysis",
    desc: "Track performance over time with gap-aware weekly snapshots.",
    link: "/trend",
    linkLabel: "View example trend",
  },
  {
    title: "Leaderboards",
    desc: "Rank players by the Statlas Index or any individual metric.",
    link: "/positions",
    linkLabel: "Browse leaderboards",
  },
  {
    title: "Search",
    desc: "Find players matching specific criteria with structured multi-condition search.",
    link: "/search",
    linkLabel: "Try search",
  },
  {
    title: "Methodology",
    desc: "See exactly how every metric is calculated. The formula, the weights, and a worked example.",
    link: "/methodology",
    linkLabel: "Read the methodology",
  },
];

export default function ShowcasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Showcase</p>
      <h1 className="page__title">Try Statlas</h1>
      <p className="page__lede">
        Experience the platform with pre-loaded data. No registration required.
        Every feature uses real player data from the current season.
      </p>

      <div className="notice" style={{ marginBottom: "var(--space-6)" }}>
        <strong>Demo data.</strong> The players and statistics shown are real. Some features
        require a free account to unlock (shortlists, reports, watchlist).
      </div>

      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {DEMO_FEATURES.map((f) => (
          <Link key={f.title} href={f.link} className="card" style={{ textDecoration: "none", color: "var(--color-text-primary)", padding: "var(--space-5)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-1)" }}>{f.title}</h3>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", margin: 0 }}>{f.desc}</p>
            </div>
            <span style={{ fontSize: "var(--text-sm)", color: "var(--color-link)", whiteSpace: "nowrap", marginLeft: "var(--space-4)" }}>
              {f.linkLabel} →
            </span>
          </Link>
        ))}
      </div>

      <section
        style={{
          marginTop: "var(--space-8)",
          padding: "var(--space-6)",
          textAlign: "center",
          background: "var(--color-surface-raised)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--color-border)",
        }}
      >
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>
          Ready to unlock more?
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Create a free account to save shortlists, generate reports, and set up watchlists.
        </p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
          <Link href="/register" className="button">Sign up free</Link>
          <Link href="/pricing" className="button button--secondary">See pricing</Link>
        </div>
      </section>
    </div>
  );
}
