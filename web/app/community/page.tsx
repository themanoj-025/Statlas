import type { Metadata } from "next";
import Link from "next/link";
import { TrendingUp, Users, FileText, Star } from "lucide-react";

export const metadata: Metadata = {
  title: "Community",
  description:
    "Statlas community: trending discoveries, leaderboards, and shared insights from football analytics practitioners.",
  alternates: { canonical: "/community" },
};

const SECTIONS = [
  {
    icon: TrendingUp,
    title: "Trending Discoveries",
    description: "Players appearing in the most shortlists this week.",
    content: "Community features coming in a future phase. For now, explore player profiles and leaderboards directly.",
    link: "/positions",
    linkLabel: "Browse leaderboards",
  },
  {
    icon: Users,
    title: "Top Contributors",
    description: "Scouts and analysts generating the most reports and evaluations.",
    content: "Leaderboards will track contributions as the community grows. Start by creating your first shortlist.",
    link: "/workspace",
    linkLabel: "Open workspace",
  },
  {
    icon: FileText,
    title: "Shared Insights",
    description: "Public shortlists and analysis shared by the community.",
    content: "Public sharing will be available when team workspaces launch. Build your first shortlist to get started.",
    link: "/register",
    linkLabel: "Create account",
  },
  {
    icon: Star,
    title: "Methodology Contributions",
    description: "Community feedback on metrics, formulas, and data quality.",
    content: "Found a data error or have a suggestion? Data-accuracy reports are read first.",
    link: "mailto:data@statlas.com",
    linkLabel: "Contact us",
  },
];

export default function CommunityPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Community</p>
      <h1 className="page__title">Community</h1>
      <p className="page__lede">
        A growing community of scouts, analysts, agents, and fans who use data-driven
        football analytics. Community features will expand as the platform grows.
      </p>

      <div className="notice" style={{ marginBottom: "var(--space-6)" }}>
        <strong>Under development.</strong> Community features like shared shortlists, leaderboards,
        and contributor rankings are planned for a future phase. The core analytics platform is
        fully available now.
      </div>

      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const isExternal = s.link.startsWith("mailto:");
          return (
            <div key={s.title} className="card" style={{ padding: "var(--space-5)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
                <h2 style={{ fontSize: "var(--text-base)", margin: 0 }}>{s.title}</h2>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)" }}>
                {s.description}
              </p>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-3)" }}>
                {s.content}
              </p>
              {isExternal ? (
                <a href={s.link} style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>{s.linkLabel} →</a>
              ) : (
                <Link href={s.link} style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>{s.linkLabel} →</Link>
              )}
            </div>
          );
        })}
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
          Join the community
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Start with the free tier. Create shortlists, compare players, and explore the data.
        </p>
        <Link href="/register" className="button">Get started</Link>
      </section>
    </div>
  );
}
