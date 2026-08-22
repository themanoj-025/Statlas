import type { Metadata } from "next";
import Link from "next/link";
import { Search, GitCompare, FolderOpen, FileText, TrendingUp, Clock } from "lucide-react";

export const metadata: Metadata = {
  title: "For Scouts & Talent Identification",
  description:
    "Cut research time in half with structured search, radar comparisons, trend analysis, and grounded AI scouting reports — every number traceable to its source.",
  alternates: { canonical: "/use-cases/scout" },
};

const STEPS = [
  {
    step: 1,
    title: "Search for candidates",
    description:
      "Use structured search with up to 8 conditions — position, age, league, metrics — to find players matching your scouting profile. Every result carries the raw values behind each condition.",
    icon: Search,
  },
  {
    step: 2,
    title: "Compare side-by-side",
    description:
      "Overlay up to 4 players on a radar chart. Matched strengths and key differences are explained from the percentile data, not hand-written copy.",
    icon: GitCompare,
  },
  {
    step: 3,
    title: "Organise shortlists",
    description:
      "Move candidates through a six-stage pipeline: discovered, monitoring, scouted, shortlisted, reviewed, signed or rejected. Every status change carries who, when, and why.",
    icon: FolderOpen,
  },
  {
    step: 4,
    title: "Generate grounded reports",
    description:
      "AI-generated scouting reports with a verification gate — every claim is checked against the data before the report is finalised. Export as PDF, JSON, or CSV.",
    icon: FileText,
  },
  {
    step: 5,
    title: "Track development over time",
    description:
      "Weekly snapshot trends show real improvement. Gaps are drawn as gaps, never interpolated. Anomaly-flagged snapshots are marked explicitly.",
    icon: TrendingUp,
  },
];

const FEATURES_HIGHLIGHTED = [
  "Structured search with 8+ conditions",
  "Workspace collaboration with notes and tags",
  "Trend analysis with gap-aware history",
  "Event-level shot and pass maps",
  "AI reports verified against real data",
  "Watchlist alerts for percentile movement",
];

export default function ScoutUseCasePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Use case</p>
      <h1 className="page__title">For scouts &amp; talent identification</h1>
      <p className="page__lede">
        Statlas cuts research time in half. Every number is backed by a published methodology,
        so you trust what you see before you act on it.
      </p>

      {/* Stats */}
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
            10+
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            hours saved per week
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>
            8
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            search conditions
          </div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div className="num" style={{ fontSize: "var(--text-3xl)", fontWeight: 700, color: "var(--color-primary)" }}>
            50K+
          </div>
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            player profiles
          </div>
        </div>
      </div>

      {/* Workflow */}
      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>
        The scout workflow
      </h2>
      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.step}
              className="card"
              style={{ display: "flex", gap: "var(--space-4)", alignItems: "flex-start", padding: "var(--space-5)" }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-primary-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Icon size={20} color="var(--color-primary)" aria-hidden="true" />
              </div>
              <div>
                <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-1)" }}>
                  {s.step}. {s.title}
                </h3>
                <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                  {s.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Features highlighted */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-3)" }}>
          Features for scouts
        </h2>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {FEATURES_HIGHLIGHTED.map((f) => (
            <li
              key={f}
              style={{
                padding: "var(--space-3) 0",
                borderBottom: "1px solid var(--color-divider)",
                fontSize: "var(--text-sm)",
                color: "var(--color-text-secondary)",
              }}
            >
              {f}
            </li>
          ))}
        </ul>
      </section>

      {/* CTA */}
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
          Start scouting smarter
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Free tier with real data. No credit card required.
        </p>
        <Link href="/register" className="button">
          Get started
        </Link>
      </section>
    </div>
  );
}
