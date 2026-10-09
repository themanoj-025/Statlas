import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Leaderboards — position groups",
  description:
    "Browse qualifying players by position group: Goalkeepers, Centre-backs, Full-backs, Defensive midfielders, Central midfielders, Attacking midfielders, Wide attackers and Strikers — across Tier 1, 2 and 3 leagues.",
  alternates: { canonical: "/positions" },
};

export default async function PositionsPage() {
  const [meta, positionData, leagues] = await Promise.all([api.meta(), api.positions(), api.leagues()]);
  const byCode = new Map(positionData.map((p) => [p.code, p]));

  return (
    <div className="container page">
      <p className="kicker">Leaderboards</p>
      <h1 className="page__title">Position groups</h1>
      <p className="page__lede">
        Every qualifying player, grouped by position and ranked by the Statlas Index (or any
        metric). Percentiles are computed within position group × league tier — pick a group, then
        a league, then sort by whatever matters.
      </p>

      <div className="grid">
        {meta.position_groups.map((group) => {
          const counts = byCode.get(group.code)?.qualifying_counts;
          const tier1Count = counts?.tier_1 ?? 0;
          return (
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
                {tier1Count.toLocaleString()} qualifying in Tier 1
              </span>
            </Link>
          );
        })}
      </div>

      <div className="section-head">
        <h2>Leagues in coverage</h2>
      </div>
      <div className="grid">
        {leagues.map((league) => (
          <Link
            key={league.slug}
            href={`/leagues/${league.slug}/index`}
            className="position-card grid__span-3"
          >
            <span className="position-card__name" style={{ display: "block" }}>
              {league.name}
            </span>
            <span className="position-card__meta">
              {league.tier_label} · {league.seasons_available[0] ?? "no data ingested yet"}
              {league.has_fbref_coverage ? "" : " · coverage pending"}
            </span>
          </Link>
        ))}
      </div>

    </div>
  );
}
