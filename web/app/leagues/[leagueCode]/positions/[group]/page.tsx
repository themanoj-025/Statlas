import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { LeaderboardTable } from "@/components/LeaderboardTable";
import { RecencyLine } from "@/components/RecencyLine";

type Props = {
  params: Promise<{ leagueCode: string; group: string }>;
};

const GROUP_CODES = new Set(["gk", "cb", "fb", "dm", "cm", "am", "w", "st"]);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { leagueCode, group } = await params;
  const [leagues, meta] = await Promise.all([api.leagues(), api.meta()]);
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league || !GROUP_CODES.has(group)) return { title: "Page not found" };
  const pos = meta.position_groups.find((p) => p.code === group.toUpperCase());
  const season = league.seasons_available[0] ?? "";
  return {
    title: `${pos?.plural ?? group} leaderboard — ${league.name} ${season}`,
    description: `Every qualifying ${pos?.plural.toLowerCase() ?? group} in ${league.name} ${season}, ranked by the selected metric. Percentiles within ${league.tier_label}, per the published methodology.`,
    alternates: { canonical: `/leagues/${leagueCode}/positions/${group}` },
  };
}

export default async function PositionPage({ params }: Props) {
  const { leagueCode, group } = await params;
  const [leagues, meta] = await Promise.all([api.leagues(), api.meta()]);
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league || !GROUP_CODES.has(group)) notFound();

  const pos = meta.position_groups.find((p) => p.code === group.toUpperCase());
  const season = league.seasons_available[0] ?? "2025-26";
  const initial = await api.leaderboard({
    league: leagueCode,
    position: group.toUpperCase(),
    metric: "si_index",
    season,
    limit: 25,
  });

  return (
    <div className="container page">
      <Breadcrumbs
        crumbs={[
          { label: "Leaderboards", href: "/positions" },
          { label: league.name, href: `/leagues/${leagueCode}/stats` },
          { label: pos?.plural ?? group },
        ]}
      />
      <h1 className="page__title">
        {pos?.plural} — {league.name} {season}
      </h1>
      <p className="page__lede">
        Qualifying {pos?.plural.toLowerCase() ?? group} in {league.name}, ranked by the selected
        metric. Percentiles are computed within {league.tier_label} — a Tier 1 percentile is not
        directly comparable to a Tier 2 percentile (methodology).
      </p>
      <RecencyLine snapshotDate={initial.entries[0]?.snapshot_date} />
      <LeaderboardTable
        initial={initial}
        season={season}
        meta={{ metrics: meta.metrics, position_groups: meta.position_groups }}
        fixedLeague={leagueCode}
        fixedPosition={group.toUpperCase()}
        title={`${pos?.plural} — ${league.name}`}
      />
    </div>
  );
}
