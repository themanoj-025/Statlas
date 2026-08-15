import type { Metadata } from "next";
import { api } from "@/lib/api";
import { TrendTool } from "@/components/TrendTool";
import { DEFAULT_TREND_METRICS, decodeTrendQuery, ogImageUrl, sharePageUrl } from "@/lib/share";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function readString(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

/**
 * /trend — the snapshot-history tool (Phase 3 — Part A). Trend charts are
 * computed from versioned weekly snapshots (never per-match data — the chart
 * states its granularity). The `?players=&metrics=&window=&mode=` form is the
 * shareable permalink; its og:image renders the real lines with the real data.
 */
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const s = readString(value);
    if (s) query.set(key, s);
  }
  const config = decodeTrendQuery(query.toString());
  const hasConfig = config.players.length > 0;
  const title = hasConfig
    ? `Snapshot trend — ${config.players.map((s) => s.replace(/-/g, " ")).join(" vs ")}`
    : "Trend — snapshot history charts";

  return {
    title,
    description: hasConfig
      ? `Snapshot-by-snapshot trend for ${config.players.length} player${config.players.length === 1 ? "" : "s"} across ${config.metrics.length} metric${config.metrics.length === 1 ? "" : "s"} — raw per-90 and percentile views, honest about gaps in the history.`
      : "Track how a player's per-90 statistics and percentiles evolve across weekly snapshots, overlay up to 3 players and multiple metrics, and share a permalink.",
    alternates: { canonical: "/trend" },
    robots: hasConfig ? { index: false, follow: true } : undefined,
    openGraph: hasConfig
      ? {
          title,
          url: sharePageUrl("trend", query.toString()),
          images: [{ url: ogImageUrl("trend", query.toString()) }],
        }
      : undefined,
  };
}

export default async function TrendPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const s = readString(value);
    if (s) query.set(key, s);
  }
  const config = decodeTrendQuery(query.toString());
  const meta = await api.meta();

  // Bound the requested metrics to the registry (decode is syntactic; the
  // registry is the arbiter of what exists — methodology-as-code).
  const metrics = config.metrics.filter((id) => meta.metrics[id]);
  const initial = {
    players: config.players.map((slug) => ({ slug })),
    metrics: metrics.length ? metrics : [...DEFAULT_TREND_METRICS],
    window: config.window,
    mode: config.mode,
  };

  return (
    <div className="container page">
      <h1 className="page__title">Trend</h1>
      <p className="page__lede">
        How a player&rsquo;s numbers evolve across weekly snapshots. Overlay up to 3 players and
        several metrics; dashed segments mark missing snapshot history — never interpolated. The
        chart states its granularity explicitly: snapshot-level, not per-match.
      </p>
      <TrendTool initial={initial} metricMeta={meta.metrics} />
    </div>
  );
}
