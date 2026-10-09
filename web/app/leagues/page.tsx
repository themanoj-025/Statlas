import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Leagues — Statlas",
  description: "Browse football leagues by tier and region. Statlas covers top leagues worldwide with per-90 statistics, similarity analytics, and emerging-player detection.",
  alternates: { canonical: "/leagues" },
};

export default async function LeaguesIndexPage() {
  const leagues = await api.leagues();

  // Group by tier.
  const tiers: Record<string, typeof leagues> = {};
  for (const l of leagues) {
    tiers[l.tier] = tiers[l.tier] ?? [];
    tiers[l.tier].push(l);
  }
  const tierOrder = ["tier_1", "tier_2", "tier_3"];
  const tierLabels: Record<string, string> = {
    tier_1: "Tier 1",
    tier_2: "Tier 2",
    tier_3: "Tier 3",
  };

  return (
    <div className="container page">
      <h1 className="page__title">Leagues</h1>
      <p className="page__lede">
        Browse every league Statlas covers. Each page features category leaderboards, emerging-player
        detection, and team overview — built from per-90 statistics, not match results.
      </p>

      {tierOrder.map((tier) => {
        const items = tiers[tier];
        if (!items?.length) return null;
        return (
          <section key={tier} style={{ marginBottom: "var(--space-6)" }}>
            <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>
              {tierLabels[tier] ?? tier}
            </h2>
            <ul
              style={{
                listStyle: "none",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: "var(--space-3)",
                margin: 0,
                padding: 0,
              }}
            >
              {items.map((l) => (
                <li key={l.slug}>
                  <Link
                    href={`/leagues/${l.slug}`}
                    style={{
                      display: "block",
                      padding: "var(--space-3) var(--space-4)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius)",
                      transition: "border-color 0.15s",
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{l.name}</div>
                    <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: "var(--space-1)" }}>
                      {l.country} · {l.team_count} teams
                      {l.has_fbref_coverage ? " · FBref" : ""}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
