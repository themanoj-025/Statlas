import type { Metadata } from "next";
import { Assistant } from "@/components/Assistant";
import { CompareTool } from "@/components/CompareTool";
import { decodeRadarQuery, ogImageUrl, sharePageUrl } from "@/lib/share";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function readString(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

/**
 * /compare — the Compare tool (site-map.md §1.1). The `?players=&mode=` query
 * form is the shareable permalink: it encodes the EXACT chart state, and the
 * og:image below renders that state's real data. Query variants stay noindex
 * (filter state is not an index target); the canonical form is /compare.
 */
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const query = new URLSearchParams();
  const players = readString(params.players);
  const mode = readString(params.mode);
  if (players) query.set("players", players);
  if (mode) query.set("mode", mode);

  const hasConfig = Boolean(players);
  const config = decodeRadarQuery(query.toString());
  const title = hasConfig
    ? `Player comparison — ${config.players.map((s) => s.replace(/-/g, " ")).join(" vs ")}`
    : "Compare — player radar overlay";

  return {
    title,
    description: hasConfig
      ? `Overlay radar for ${config.players.length} players (${config.mode === "pct" ? "percentile" : "raw per-90"} view) — Statlas, with a fully published methodology.`
      : "Overlay up to 4 players' percentile radars on a single chart, with a percentile / raw per-90 toggle.",
    alternates: { canonical: "/compare" },
    robots: hasConfig ? { index: false, follow: true } : undefined,
    openGraph: hasConfig
      ? {
          title,
          url: sharePageUrl("radar", query.toString()),
          images: [{ url: ogImageUrl("radar", query.toString()) }],
        }
      : undefined,
  };
}

export default async function ComparePage({ searchParams }: Props) {
  const params = await searchParams;
  const query = new URLSearchParams();
  const players = readString(params.players);
  const mode = readString(params.mode);
  if (players) query.set("players", players);
  if (mode) query.set("mode", mode);
  const initial = decodeRadarQuery(query.toString());

  return (
    <div className="container page">
      <CompareTool initial={initial} />
      {/* Phase 4 B — the grounded assistant lives where the analysis happens,
          not on an isolated page (the original DataMB gap this fixes). */}
      <div style={{ marginTop: "var(--space-4)" }}>
        <Assistant />
      </div>
    </div>
  );
}
