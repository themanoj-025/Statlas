import type { Metadata } from "next";
import Link from "next/link";
import { Radar, GitCompare, Share2, BookOpen, TrendingUp } from "lucide-react";

export const metadata: Metadata = {
  title: "For Football Fans",
  description:
    "Understand the game deeper. Percentile ranks, radar comparisons, and trend charts — all with a published methodology you can verify.",
  alternates: { canonical: "/use-cases/fan" },
};

const STEPS = [
  {
    step: 1,
    title: "Search for your favourite players",
    description:
      "Look up any qualifying player across Tier 1\u20133 leagues. Free tier gives you full player pages with percentiles and the Statlas Index.",
    icon: Radar,
  },
  {
    step: 2,
    title: "See their percentile rank",
    description:
      "Every metric is compared to positional peers in the same league tier. A percentile of 87 means \u201cexceeds 87% of qualifying peers.\u201d",
    icon: TrendingUp,
  },
  {
    step: 3,
    title: "Compare to idols",
    description:
      "Overlay up to 4 players on a radar chart. See strengths and weaknesses at a glance. Share the comparison with friends.",
    icon: GitCompare,
  },
  {
    step: 4,
    title: "Learn the methodology",
    description:
      "Every number links to its definition. Understand how percentiles are calculated, what the Statlas Index measures, and what it deliberately does not.",
    icon: BookOpen,
  },
  {
    step: 5,
    title: "Share with friends",
    description:
      "Shareable permalinks and embeddable widgets. Every embed carries Statlas attribution and links to the methodology.",
    icon: Share2,
  },
];

export default function FanUseCasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Use case</p>
      <h1 className="page__title">For football fans</h1>
      <p className="page__lede">
        Understand the game deeper. Percentile ranks, radar comparisons, and trend charts \u2014
        all grounded in a published methodology you can verify.
      </p>

      <div className="card" style={{ display: "flex", justifyContent: "center", gap: "var(--space-8)", padding: "var(--space-5)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>50K+</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>player profiles</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>16</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>tracked metrics</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>3</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>league tiers</div>
        </div>
      </div>

      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Get started</h2>
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.step} className="card" style={{ display: "flex", gap: "var(--space-4)", alignItems: "flex-start", padding: "var(--space-5)" }}>
              <div style={{ width: 40, height: 40, borderRadius: "var(--radius-md)", background: "var(--color-primary-muted)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Icon size={20} color="var(--color-primary)" aria-hidden="true" />
              </div>
              <div>
                <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-1)" }}>{s.step}. {s.title}</h3>
                <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>{s.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      <section style={{ marginTop: "var(--space-8)", padding: "var(--space-6)", textAlign: "center", background: "var(--color-surface-raised)", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Join 100K+ fans</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>Free tier with real data. No credit card required.</p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/positions" className="button">Browse leaderboards</Link>
          <Link href="/compare" className="button button--secondary">Compare players</Link>
        </div>
      </section>
    </div>
  );
}
