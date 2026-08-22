import type { Metadata } from "next";
import Link from "next/link";
import { BookOpen, Code, Database, BarChart3, FileJson } from "lucide-react";

export const metadata: Metadata = {
  title: "For Data Scientists & Analysts",
  description:
    "Audit every claim against published methodology. API access, data export, and a metric registry you can verify.",
  alternates: { canonical: "/use-cases/analyst" },
};

const STEPS = [
  {
    step: 1,
    title: "Access published methodology",
    description:
      "Every metric — including the Statlas Index — has a registry entry with name, formula, units, source precedence, and qualification threshold. The methodology page is generated from the registry.",
    icon: BookOpen,
  },
  {
    step: 2,
    title: "Verify metric calculations",
    description:
      "Worked examples with real player data show the full arithmetic end-to-end. Percentile formulas, position weights, and the composite index are all reproducible.",
    icon: BarChart3,
  },
  {
    step: 3,
    title: "Run custom queries",
    description:
      "Structured search with up to 8 conditions. Export results as CSV or JSON. API access on the Business tier with documented rate limits.",
    icon: Code,
  },
  {
    step: 4,
    title: "Export data for analysis",
    description:
      "Every stat block, leaderboard, and trend chart carries its snapshot date. Data is append-only and versioned by scrape date — historical values are never overwritten.",
    icon: FileJson,
  },
  {
    step: 5,
    title: "Integrate into your stack",
    description:
      "Embeddable radar and trend widgets for dashboards. Versioned REST API with OpenAPI specification. Webhook support for automation.",
    icon: Database,
  },
];

export default function AnalystUseCasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Use case</p>
      <h1 className="page__title">For data scientists &amp; analysts</h1>
      <p className="page__lede">
        Audit every claim. Statlas publishes its methodology as code — the formula in the
        registry is the formula the site uses. If you find a discrepancy, that is a bug.
      </p>

      <div className="card" style={{ display: "flex", justifyContent: "center", gap: "var(--space-8)", padding: "var(--space-5)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>16</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>registry metrics</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>v1</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>versioned API</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>JSON</div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>export format</div>
        </div>
      </div>

      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>The analyst workflow</h2>
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
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Access the data layer</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>API access on the Business tier. Full methodology documented.</p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/methodology" className="button">View methodology</Link>
          <Link href="/api-docs" className="button button--secondary">API docs</Link>
        </div>
      </section>
    </div>
  );
}
