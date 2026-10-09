import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { LeaderboardTable } from "@/components/LeaderboardTable";
import { RecencyLine } from "@/components/RecencyLine";

type Props = {
  params: Promise<{ leagueCode: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { leagueCode } = await params;
  const leagues = await api.leagues();
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league) return { title: "League not found" };
  const season = league.seasons_available[0] ?? "";
  return {
    title: `${league.name} ${season} Statlas Index`,
    description: `The ${league.name} ${season} leaderboard ranked by the Statlas Index — the weighted average of each player's percentile ranks within ${league.tier_label}.`,
    alternates: { canonical: `/leagues/${leagueCode}/index` },
  };
}

export default async function LeagueIndexPage({ params }: Props) {
  const { leagueCode } = await params;
  const leagues = await api.leagues();
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league) notFound();

  const season = league.seasons_available[0] ?? "2025-26";
  const [meta, initial] = await Promise.all([
    api.meta(),
    api.leaderboard({ league: leagueCode, metric: "si_index", season, limit: 25 }),
  ]);
  const latest = initial.entries[0]?.snapshot_date;

  return (
    <div className="container page">
      <Breadcrumbs
        crumbs={[
          { label: "Leaderboards", href: "/positions" },
          { label: league.name, href: `/leagues/${leagueCode}/stats` },
          { label: "Statlas Index" },
        ]}
      />
      <h1 className="page__title">{league.name} — Statlas Index {season}</h1>
      <p className="page__lede">
        Every qualifying player in {league.name}, ranked by the Statlas Index — a weighted average
        of percentile ranks within position group × league tier, per the published methodology.
      </p>
      <RecencyLine snapshotDate={latest} />
      <LeaderboardTable
        initial={initial}
        season={season}
        meta={{ metrics: meta.metrics, position_groups: meta.position_groups }}
        fixedLeague={leagueCode}
        title={`${league.name} — Statlas Index`}
      />
    </div>
  );
}
