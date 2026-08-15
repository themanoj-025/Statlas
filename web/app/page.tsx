import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { formatNumber, percentileBand, positionGroupLabel } from "@/lib/format";

export const metadata: Metadata = {
  title: "Statlas — football analytics that shows its work",
  description:
    "Per-90 statistics, percentile ranks and the Statlas Index for football players across Tier 1–3 leagues, with a fully published methodology.",
};

export default async function HomePage() {
  const [meta, leaderboard, leagues, positions] = await Promise.all([
    api.meta(),
    api.leaderboard({ metric: "si_index", tier: "tier_1", position: "ST", season: "2025-26", limit: 10 }),
    api.leagues(),
    api.positions(),
  ]);

  const inCoverage = leagues.filter((l) => l.has_fbref_coverage);
  const tier1Leagues = inCoverage.filter((l) => l.tier === "tier_1");
  const season = leaderboard.entries[0]?.snapshot_date?.slice(0, 10) ?? "";

  return (
    <div className="container page">
      <div className="hero">
        <div>
          <p className="kicker">Statlas</p>
          <h1>Football analytics that shows its work.</h1>
          <p>
            Per-90 statistics, percentile ranks and the Statlas Index for every qualifying player —
            every metric traces to a published formula. No black box, no fabricated numbers, no
            marketing.
          </p>
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <Link className="button" href="/positions">
              Browse leaderboards
            </Link>
            <Link className="button button--secondary" href="/compare">
              Compare players
            </Link>
          </div>
        </div>

        <div className="card card--flush">
          <div style={{ padding: "var(--space-3) var(--space-4)", borderBottom: "1px solid var(--color-divider)" }}>
            <h2 style={{ fontSize: "var(--text-base)", margin: 0 }}>
              Tier 1 · Strikers · Statlas Index {season}
            </h2>
          </div>
          <div className="table-wrap" style={{ border: "none", borderRadius: 0 }}>
            <table className="table" aria-label="Tier 1 strikers ranked by the Statlas Index">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Player</th>
                  <th scope="col">Club</th>
                  <th scope="col">Index</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.entries.map((entry, index) => (
                  <tr key={entry.player_id}>
                    <td className="num">{index + 1}</td>
                    <td>
                      {entry.slug ? <Link href={`/players/${entry.slug}`}>{entry.name}</Link> : entry.name}
                    </td>
                    <td>{entry.club ?? "—"}</td>
                    <td className="num" style={{ color: percentileBand(entry.value), fontWeight: 600 }}>
                      {formatNumber(entry.value, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: "var(--space-3) var(--space-4)", borderTop: "1px solid var(--color-divider)" }}>
            <Link href="/leagues/premier-league/positions/st" style={{ fontSize: "var(--text-sm)" }}>
              Full striker leaderboard <ArrowRight size={12} aria-hidden="true" style={{ verticalAlign: "middle" }} />
            </Link>
          </div>
        </div>
      </div>

      <div className="section-head">
        <h2>Position groups</h2>
        <Link href="/positions" style={{ fontSize: "var(--text-sm)" }}>
          All groups →
        </Link>
      </div>
      <div className="grid">
        {positions.map((group) => (
          <Link
            key={group.code}
            href={`/leagues/premier-league/positions/${group.code.toLowerCase()}`}
            className="position-card grid__span-3"
          >
            <span className="position-card__code">{group.code}</span>
            <span className="position-card__name" style={{ display: "block" }}>
              {group.plural}
            </span>
            <span className="position-card__meta">
              {(group.qualifying_counts?.tier_1 ?? 0).toLocaleString()} qualifying in Tier 1
            </span>
          </Link>
        ))}
      </div>

      <div className="section-head">
        <h2>Leagues in coverage</h2>
        <Link href="/data-coverage" style={{ fontSize: "var(--text-sm)" }}>
          Data coverage →
        </Link>
      </div>
      <div className="grid">
        {tier1Leagues.map((league) => (
          <Link key={league.slug} href={`/leagues/${league.slug}/index`} className="position-card grid__span-3">
            <span className="position-card__name" style={{ display: "block" }}>
              {league.name}
            </span>
            <span className="position-card__meta">
              {league.tier_label} · {league.seasons_available[0] ?? "—"}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
