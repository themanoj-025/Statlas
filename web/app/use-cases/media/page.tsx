import type { Metadata } from "next";
import Link from "next/link";
import { Share2, BarChart3, FileText, Link2, TrendingUp } from "lucide-react";

export const metadata: Metadata = {
  title: "For Journalists & Content Creators",
  description:
    "Tell credible stories with data. Embeddable charts, shareable comparisons, and cited methodology for every stat you publish.",
  alternates: { canonical: "/use-cases/media" },
};

const STEPS = [
  {
    step: 1,
    title: "Search for trending players",
    description:
      "Use structured search to find players matching your story angle — age, position, league, specific metrics.",
    icon: BarChart3,
  },
  {
    step: 2,
    title: "Create shareable comparisons",
    description:
      "Up to 4 players on one radar chart. Every axis is a named metric with a published definition. Shareable permalink included.",
    icon: Share2,
  },
  {
    step: 3,
    title: "Embed interactive charts",
    description:
      "Copy-paste an embed code for radar charts, trend charts, or player cards. The embed carries Statlas attribution.",
    icon: Link2,
  },
  {
    step: 4,
    title: "Cite the methodology",
    description:
      "Every stat links back to its metric definition. Your readers can verify the numbers themselves.",
    icon: FileText,
  },
  {
    step: 5,
    title: "Track narrative trends",
    description:
      "Trend charts show real improvement over time. Gaps are drawn honestly. Use snapshot dates in your reporting.",
    icon: TrendingUp,
  },
];

export default function MediaUseCasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Use case</p>
      <h1 className="page__title">For journalists &amp; content creators</h1>
      <p className="page__lede">
        Tell credible stories with data. Every stat on Statlas links to its methodology,
        so your readers can verify the numbers themselves.
      </p>

      <div className="card" style={{ display: "flex", justifyContent: "center", gap: "var(--space-8)", padding: "var(--space-5)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>4</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>players per embed</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>HTML</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>embed codes</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>Free</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>embed allowance</div>
        </div>
      </div>

      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>The content workflow</h2>
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
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Create better content</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>Free tier with embeds. Every chart links to its methodology.</p>
        <Link href="/register" className="button">Get started</Link>
      </section>
    </div>
  );
}
