import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Image as ImageIcon, Users } from "lucide-react";
import { api } from "@/lib/api";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { RecencyLine } from "@/components/RecencyLine";
import { ReportIssue } from "@/components/ReportIssue";
import { SquadRadar } from "@/components/SquadRadar";
import { formatDate, formatNumber, initials, positionGroupLabel, tierLabel } from "@/lib/format";

type Props = {
  params: Promise<{ leagueSlug: string; teamSlug: string }>;
};

async function getTeam(leagueSlug: string, teamSlug: string) {
  try {
    return await api.team(leagueSlug, teamSlug);
  } catch (err) {
    if (err instanceof Error && "status" in err && (err as { status: number }).status === 404) return null;
    throw err;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { leagueSlug, teamSlug } = await params;
  const team = await getTeam(leagueSlug, teamSlug);
  if (!team) return { title: "Club not found" };
  const season = team.roster[0]?.season ?? "";
  return {
    title: `${team.name} — ${season} squad stats, roster and radar`,
    description: `${team.name} ${season} squad: ${team.roster_count} players, ${team.qualified_count} with a published Statlas Index. Squad-average radar vs ${tierLabel(team.tier)} peers.`,
    alternates: { canonical: `/clubs/${leagueSlug}/${teamSlug}` },
  };
}

export default async function TeamPage({ params }: Props) {
  const { leagueSlug, teamSlug } = await params;
  const team = await getTeam(leagueSlug, teamSlug);
  if (!team) notFound();

  const season = team.roster[0]?.season ?? "";
  const latestSnapshot = team.roster[0]?.snapshot_date;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SportsTeam",
    name: team.name,
    sport: "Soccer",
    member: team.roster.map((r) => ({
      "@type": "Person",
      name: r.name,
      ...(r.nationality ? { nationality: r.nationality } : {}),
    })),
    parentOrganization: { "@type": "SportsOrganization", name: team.league },
  };

  return (
    <div className="container page">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Breadcrumbs
        crumbs={[
          { label: "Leaderboards", href: "/positions" },
          { label: team.league, href: `/leagues/${leagueSlug}/stats` },
          { label: team.name },
        ]}
      />

      <div className="profile-header" style={{ marginBottom: "var(--space-5)" }}>
        <div className="profile-header__top">
          <div className="profile-header__identity">
            {team.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={team.logo_url}
                alt={`${team.name} logo`}
                width={96}
                height={96}
                style={{ borderRadius: "var(--radius-lg)" }}
              />
            ) : (
              <div className="avatar-placeholder" role="img" aria-label="No licensed logo available — honest placeholder">
                <ImageIcon size={32} aria-hidden="true" />
              </div>
            )}
            <div>
              <h1>{team.name}</h1>
              <div className="profile-header__meta">
                <span className="chip">
                  <Users size={12} aria-hidden="true" /> {team.roster_count} players
                </span>
                <span className="chip chip--primary">{tierLabel(team.tier)}</span>
                <span className="chip">{team.qualified_count} with a published index</span>
                <span className="chip">
                  {formatNumber(team.squad_radar ? Math.round(team.squad_radar.n_players) : 0, 0)} qualifying for the squad radar
                </span>
              </div>
              {!team.logo_url && (
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "var(--space-2) 0 0" }}>
                  No licensed club logo in the data set yet — shown as a placeholder until a real
                  asset exists.
                </p>
              )}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--space-2)" }}>
          <RecencyLine snapshotDate={latestSnapshot} />
          <ReportIssue context={team.name} />
        </div>
      </div>

      <div className="grid">
        <div className="grid__span-8">
          <section className="card card--flush" aria-label={`${team.name} roster`}>
            <div style={{ padding: "var(--space-3) var(--space-4)", borderBottom: "1px solid var(--color-divider)" }}>
              <h2 className="card__title" style={{ margin: 0 }}>Roster — {season}</h2>
            </div>
            <div className="table-wrap" style={{ border: "none", borderRadius: 0 }}>
              <table className="table table--sticky-first" aria-label={`${team.name} roster, sorted by Statlas Index`}>
                <thead>
                  <tr>
                    <th scope="col">Player</th>
                    <th scope="col">Position</th>
                    <th scope="col">Min</th>
                    <th scope="col">M</th>
                    <th scope="col">Index</th>
                  </tr>
                </thead>
                <tbody>
                  {team.roster.map((player) => (
                    <tr key={player.player_id}>
                      <td>
                        {player.slug ? (
                          <Link href={`/players/${player.slug}`}>{player.name}</Link>
                        ) : (
                          player.name
                        )}
                      </td>
                      <td>{positionGroupLabel(player.position_group)}</td>
                      <td className="num">{Math.round(player.minutes).toLocaleString()}</td>
                      <td className="num">{player.matches}</td>
                      <td className="num" style={{ fontWeight: 600 }}>
                        {player.index !== null ? formatNumber(player.index, 1) : <span style={{ color: "var(--color-text-secondary)" }}>pending</span>}
                      </td>
                    </tr>
                  ))}
                  {!team.roster.length && (
                    <tr>
                      <td colSpan={5}>
                        <div className="state-block state-block--sunken" role="status">
                          <p className="state-block__title">No players in this squad yet.</p>
                          <p className="state-block__body">
                            The roster is populated from stat snapshots. If {team.name} is outside
                            current data coverage, they won&rsquo;t appear until coverage expands.
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
        <div className="grid__span-4">
          <SquadRadar
            radar={team.squad_radar}
            leagueSlug={leagueSlug}
            teamName={team.name}
          />
        </div>
      </div>
    </div>
  );
}
