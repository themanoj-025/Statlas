import type { Metadata } from "next";
import Link from "next/link";
import { FileText, GitCompare, Users, TrendingUp, Share2 } from "lucide-react";

export const metadata: Metadata = {
  title: "For Agents & Negotiators",
  description:
    "Back your transfer valuations with data. Comparable player analysis, grounded reports, and embeddable charts for contract negotiations.",
  alternates: { canonical: "/use-cases/agent" },
};

const STEPS = [
  {
    step: 1,
    title: "Build a complete profile",
    description:
      "Access per-90 statistics, percentile ranks, and trend history for any qualifying player. Every number carries its snapshot date and source attribution.",
    icon: FileText,
  },
  {
    step: 2,
    title: "Find comparable players",
    description:
      "Cosine similarity over percentile vectors identifies players with statistically similar profiles. Matched strengths and key differences are explained from the data.",
    icon: GitCompare,
  },
  {
    step: 3,
    title: "Generate grounded reports",
    description:
      "AI-generated scouting reports with a verification gate. Every claim is checked against the data before the report is finalised. Export as PDF for club presentations.",
    icon: FileText,
  },
  {
    step: 4,
    title: "Share with clubs and media",
    description:
      "Embeddable radar charts and shareable permalinks let you present data-backed valuations. Every embed carries the Statlas methodology link.",
    icon: Share2,
  },
  {
    step: 5,
    title: "Track contract performance",
    description:
      "Watchlist alerts notify you when a player\u2019s percentile ranks change significantly, giving you data points for contract renegotiations.",
    icon: TrendingUp,
  },
];

export default function AgentUseCasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Use case</p>
      <h1 className="page__title">For agents &amp; negotiators</h1>
      <p className="page__lede">
        Back your valuations with data that can survive scrutiny. Every number on Statlas
        traces to a published methodology — the methodology is the product.
      </p>

      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "var(--space-8)",
          padding: "var(--space-5)",
          marginBottom: "var(--space-6)",
          flexWrap: "wrap",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>
            12
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            outfield metrics per player
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>
            4
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            players per comparison
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>
            100%
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            methodology transparency
          </div>
        </div>
      </div>

      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>
        The agent workflow
      </h2>
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
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Empower your negotiations</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>Start with the free tier. Upgrade when you need reports and embeds.</p>
        <Link href="/register" className="button">Get started</Link>
      </section>
    </div>
  );
}
