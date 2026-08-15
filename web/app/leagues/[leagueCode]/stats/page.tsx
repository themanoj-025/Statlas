import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { formatNumber, percentileBand } from "@/lib/format";

type Props = {
  params: Promise<{ leagueCode: string }>;
  searchParams: Promise<{ metric?: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { leagueCode } = await params;
  const leagues = await api.leagues();
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league) return { title: "League not found" };
  return {
    title: `${league.name} ${league.seasons_available[0] ?? ""} per-90 stats`,
    description: `Per-90 statistics for every qualifying ${league.name} player this season, ranked by the selected metric. ${league.tier_label} per the published methodology.`,
    alternates: { canonical: `/leagues/${leagueCode}/stats` },
  };
}

export default async function LeagueStatsPage({ params, searchParams }: Props) {
  const { leagueCode } = await params;
  const { metric = "si_gls_p90" } = await searchParams;

  const leagues = await api.leagues();
  const league = leagues.find((l) => l.slug === leagueCode);
  if (!league) notFound();

  const [meta, rows] = await Promise.all([
    api.meta(),
    api.leagueStats(leagueCode, { metric, limit: 300 }),
  ]);
  const metricSpec = meta.metrics[metric];
  const season = league.seasons_available[0] ?? "";

  return (
    <div className="container page">
      <Breadcrumbs
        crumbs={[
          { label: "Leaderboards", href: "/positions" },
          { label: league.name },
          { label: "Per-90 stats" },
        ]}
      />
      <h1 className="page__title">{league.name} — per-90 stats</h1>
      <p className="page__lede">
        Latest snapshot per qualifying player, {season}. Select a metric to rank by — each value is
        a real per-90 rate from the latest stat snapshot, with its sample context one click away.
      </p>

      <nav aria-label="Metric" style={{ marginBottom: "var(--space-4)" }}>
        <ul style={{ listStyle: "none", display: "flex", flexWrap: "wrap", gap: "var(--space-2)", margin: 0, padding: 0 }}>
          {Object.values(meta.metrics).map((m) => (
            <li key={m.id}>
              <Link
                href={`/leagues/${leagueCode}/stats?metric=${m.id}`}
                aria-current={m.id === metric ? "page" : undefined}
                style={
                  m.id === metric
                    ? { background: "var(--color-primary-muted)", padding: "var(--space-1) var(--space-3)", borderRadius: "var(--radius-pill)", fontSize: "var(--text-xs)", fontWeight: 600 }
                    : { fontSize: "var(--text-xs)", padding: "var(--space-1) var(--space-3)" }
                }
              >
                {m.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="table-wrap">
        <table
          className="table table--sticky-first"
          aria-label={`${league.name} per-90 stats ranked by ${metricSpec?.name ?? metric}`}
        >
          <thead>
            <tr>
              <th scope="col">Rank</th>
              <th scope="col">Player</th>
              <th scope="col">Club</th>
              <th scope="col">Pos</th>
              <th scope="col">Min</th>
              <th scope="col">M</th>
              <th scope="col">{metricSpec?.name ?? metric}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={row.player_id}>
                <td className="num">{index + 1}</td>
                <td>
                  {row.slug ? <Link href={`/players/${row.slug}`}>{row.name}</Link> : row.name}
                </td>
                <td>{row.club ?? "—"}</td>
                <td className="num">{row.position_group ?? "—"}</td>
                <td className="num">{Math.round(row.minutes).toLocaleString()}</td>
                <td className="num">{row.matches}</td>
                <td
                  className="num"
                  style={row.value !== null ? { color: percentileBand((row.status === "qualified" ? row.value : null) ?? 0), fontWeight: 600 } : { color: "var(--color-text-muted)" }}
                >
                  {row.status === "qualified" ? formatNumber(row.value, 2) : "N/A"}
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={7}>
                  <div className="state-block state-block--sunken" role="status">
                    <p className="state-block__title">No qualifying players yet.</p>
                    <p className="state-block__body">
                      No {league.name} players have a snapshot for {season} yet. Coverage appears on
                      the data coverage page as it is ingested.
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
