import type { Metadata } from "next";
import Link from "next/link";
import { Rocket, Search, FolderOpen, FileText, CheckCircle } from "lucide-react";

export const metadata: Metadata = {
  title: "Getting Started",
  description:
    "Interactive onboarding tutorial for new Statlas users. Learn how to search, compare, organise, and generate reports.",
  alternates: { canonical: "/onboarding" },
};

const STEPS = [
  {
    step: 1,
    icon: Search,
    title: "Find players",
    description: "Use the search box or leaderboards to find players. Try searching for a name or browsing by position group.",
    link: "/search",
    linkLabel: "Try search",
  },
  {
    step: 2,
    icon: Rocket,
    title: "Compare players",
    description: "Select 2-4 players to see them on a radar chart. Every axis shows a named metric with a published definition.",
    link: "/compare",
    linkLabel: "Open comparison tool",
  },
  {
    step: 3,
    icon: FolderOpen,
    title: "Create a shortlist",
    description: "Save players to a shortlist and move them through the status pipeline. Add notes and tags as you go.",
    link: "/workspace",
    linkLabel: "Open workspace",
  },
  {
    step: 4,
    icon: FileText,
    title: "Generate a report",
    description: "AI-generated scouting reports with every claim verified against real data. Export as PDF, JSON, or CSV.",
    link: "/reports",
    linkLabel: "View reports",
  },
  {
    step: 5,
    icon: CheckCircle,
    title: "You're all set",
    description: "Explore the methodology to understand how every number is calculated. The formula is published as code.",
    link: "/methodology",
    linkLabel: "Read the methodology",
  },
];

export default function OnboardingPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
      <p className="kicker">Getting started</p>
      <h1 className="page__title">Welcome to Statlas</h1>
      <p className="page__lede">
        Five steps to get the most out of the platform. Every feature uses real data with a
        published methodology.
      </p>

      <div style={{ display: "grid", gap: "var(--space-4)" }}>
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.step} className="card" style={{ padding: "var(--space-5)", display: "flex", gap: "var(--space-4)", alignItems: "flex-start" }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "var(--radius-lg)",
                  background: "var(--color-primary-muted)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Icon size={24} color="var(--color-primary)" aria-hidden="true" />
              </div>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-1)" }}>
                  Step {s.step}: {s.title}
                </h3>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)" }}>
                  {s.description}
                </p>
                <Link href={s.link} style={{ fontSize: "var(--text-sm)", fontWeight: 600 }}>
                  {s.linkLabel} →
                </Link>
              </div>
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
          Ready to start?
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Create a free account to unlock all features.
        </p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
          <Link href="/register" className="button">Sign up free</Link>
          <Link href="/positions" className="button button--secondary">Browse leaderboards</Link>
        </div>
      </section>
    </div>
  );
}
