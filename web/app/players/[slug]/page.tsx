import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { CalendarDays, Flag, MapPin, Shield, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { AddToShortlist } from "@/components/AddToShortlist";
import { GenerateReport } from "@/components/GenerateReport";
import { KeyStats } from "@/components/KeyStats";
import { RadarCard } from "@/components/RadarCard";
import { RecencyLine } from "@/components/RecencyLine";
import { SimilarPlayers } from "@/components/SimilarPlayers";
import { TrendCard } from "@/components/TrendCard";
import { EventMaps } from "@/components/EventMaps";
import { ReportIssue } from "@/components/ReportIssue";
import { formatDate, formatNumber, positionGroupLabel, tierLabel } from "@/lib/format";

type Props = {
  params: Promise<{ slug: string }>;
};

async function getPayload(slug: string) {
  try {
    return await api.playerBySlug(slug);
  } catch (err) {
    if (err instanceof Error && "status" in err && (err as { status: number }).status === 404) {
      return null;
    }
    throw err;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const payload = await getPayload(slug);
  if (!payload) return { title: "Player not found" };

  const { player, percentiles, sentence, raw } = payload;
  const title = `${player.name} — ${[player.club, positionGroupLabel(player.position_group)].filter(Boolean).join(" ")}${raw.season ? ` ${raw.season}` : ""}`;
  const description =
    sentence ||
    `${player.name} — per-90 statistics, percentile ranks and the Statlas Index.` +
      (raw.snapshot_date ? ` Data as of ${formatDate(raw.snapshot_date)}.` : "");
  const canonicalSlug = player.canonical_slug ?? player.slug ?? slug;

  return {
    title,
    description,
    alternates: { canonical: `/players/${canonicalSlug}` },
    openGraph: {
      type: "profile",
      title,
      description,
      url: `/players/${canonicalSlug}`,
      images: [{ url: `/players/${canonicalSlug}/opengraph-image` }],
    },
  };
}

export default async function PlayerPage({ params }: Props) {
  const { slug } = await params;
  const [payload, coverage, meta] = await Promise.all([
    getPayload(slug),
    api.coverage().catch(() => null),
    api.meta().catch(() => null),
  ]);

  if (!payload) notFound();

  // Part B4: the covered StatsBomb competitions the honest note can name.
  const coveredCompetitions = coverage?.statsbomb_competitions
    .filter((c) => c.status === "active")
    .map((c) => `${c.competition_name} ${c.seasons_available.join(", ") || ""}`.trim())
    ?? [];

  const { player, percentiles, raw, axes, sentence, similar } = payload;
  // site-map.md §4: non-canonical slugs get a PERMANENT redirect to the
  // canonical URL (the App Router's permanentRedirect serves 308, the
  // modern permanent-redirect status — search engines treat it like 301).
  const canonicalSlug = player.canonical_slug ?? player.slug ?? slug;
  if (canonicalSlug !== slug) permanentRedirect(`/players/${canonicalSlug}`);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: player.name,
    ...(player.date_of_birth ? { birthDate: player.date_of_birth } : {}),
    ...(player.nationality ? { nationality: player.nationality } : {}),
    jobTitle: player.position_label ?? positionGroupLabel(player.position_group),
    ...(player.club
      ? {
          affiliation: {
            "@type": "SportsTeam",
            name: player.club,
            ...(raw.league ? { parentOrganization: { "@type": "SportsOrganization", name: raw.league } } : {}),
          },
        }
      : {}),
  };

  const hasIndex = percentiles.index !== null;
  const pendingMinutes = raw.minutes_played < payload.qualifying_minutes;

  return (
    <div className="container page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="profile-header">
        <div className="profile-header__top">
          <div className="profile-header__identity">
            <div className="avatar-placeholder no-print" aria-hidden="true">
              {player.name
                .split(/\s+/)
                .slice(0, 2)
                .map((part) => part[0]?.toUpperCase())
                .join("")}
            </div>
            <div>
              <h1>{player.name}</h1>
              <div className="profile-header__meta">
                {player.club && (
                  <span className="chip">
                    <Shield size={12} aria-hidden="true" /> {player.club}
                  </span>
                )}
                {player.position_group && <span className="chip chip--primary">{positionGroupLabel(player.position_group)}</span>}
                {player.nationality && (
                  <span className="chip">
                    <Flag size={12} aria-hidden="true" /> {player.nationality}
                  </span>
                )}
                {player.age !== null && player.age !== undefined && (
                  <span className="chip">
                    <CalendarDays size={12} aria-hidden="true" /> {player.age} years
                  </span>
                )}
                {raw.league && (
                  <span className="chip">
                    <MapPin size={12} aria-hidden="true" /> {raw.league} · {tierLabel(raw.league_tier)}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "var(--space-2)" }}>
            {hasIndex ? (
              <span className="badge" style={{ minWidth: 72 }} aria-label={`Statlas Index ${percentiles.index?.toFixed(1)} of 100`}>
                {formatNumber(percentiles.index, 1)}
              </span>
            ) : pendingMinutes ? (
              <span className="chip chip--accent">
                Pending qualification — needs {Math.ceil(payload.qualifying_minutes - raw.minutes_played)} more minutes
              </span>
            ) : (
              <span className="chip">Index pending</span>
            )}
            <div className="no-print" style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", justifyContent: "flex-end" }}>
              {player.slug && (
                <Link className="button button--sm" href={`/compare?players=${player.slug}`}>
                  Compare
                </Link>
              )}
              <AddToShortlist playerId={player.player_id} playerName={player.name} compact />
              <GenerateReport playerId={player.player_id} playerName={player.name} compact />
              <ReportIssue context={player.name} />
            </div>
          </div>
        </div>

        {sentence && <p className="data-sentence">{sentence}</p>}

        <RecencyLine
          snapshotDate={percentiles.snapshot_date ?? raw.snapshot_date}
          computedDate={percentiles.computed_date}
          source={raw.source}
        />
      </div>

      <div className="grid" style={{ marginTop: "var(--space-5)" }}>
        <div className="grid__span-8">
          <RadarCard
            slugs={[canonicalSlug]}
            title={`Per-90 percentiles vs ${tierLabel(raw.league_tier)} ${positionGroupLabel(player.position_group).toLowerCase()}s · ${raw.season ?? ""}`}
            subtitle="Percentile ranks within position group × league tier, per the published methodology"
          />
        </div>
        <div className="grid__span-4" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <KeyStats axes={axes} />
        </div>
      </div>

      <div style={{ marginTop: "var(--space-4)" }}>
        <div className="section-head">
          <h2>Snapshot history</h2>
          <Link href={`/trend?players=${player.slug}`} className="button button--sm button--secondary">
            <TrendingUp size={14} aria-hidden="true" /> Open in Trend
          </Link>
        </div>
        <TrendCard
          playerId={player.player_id}
          playerName={player.name}
          playerSlug={canonicalSlug}
          metricMeta={meta?.metrics ?? {}}
        />
      </div>

      <EventMaps
        playerId={player.player_id}
        playerName={player.name}
        coveredCompetitions={coveredCompetitions}
        initialCoverage={payload.event_coverage}
      />

      <div style={{ marginTop: "var(--space-4)" }}>
        <SimilarPlayers playerId={player.player_id} playerName={player.name} />
      </div>
    </div>
  );
}
