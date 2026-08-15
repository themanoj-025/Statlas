import type { NextRequest } from "next/server";
import { api } from "@/lib/api";
import { OG_METRIC_DASHES, OG_PLAYER_COLORS, ogFooter, trendChartSvg } from "@/lib/chartSvg";
import { renderOgCard } from "@/lib/ogRender";
import { DEFAULT_TREND_METRICS, decodeTrendQuery } from "@/lib/share";

export const runtime = "nodejs";

/**
 * Dynamic OG image for a shared trend permalink (Part C2): the actual lines,
 * with gap segments dashed and the real final values labelled — the preview
 * is the chart, not a placeholder.
 */
export async function GET(request: NextRequest) {
  const config = decodeTrendQuery(request.nextUrl.searchParams.toString());

  const [meta, resolved] = await Promise.all([
    api.meta().catch(() => null),
    Promise.all(
      config.players.map((slug) => api.playerBySlug(slug).catch(() => null))
    ),
  ]);
  const payloads = resolved.filter((p): p is NonNullable<typeof p> => p !== null);
  // Mirror the page: a link without metrics renders with the tool's defaults,
  // so the preview must draw the same lines the page would (C2 honesty).
  const fromQuery = config.metrics.filter((id) => meta?.metrics[id]);
  const resolvedMetrics = fromQuery.length
    ? fromQuery
    : DEFAULT_TREND_METRICS.filter((id) => meta?.metrics[id]);

  let series: {
    label: string;
    color: string;
    dash: string;
    points: { date: string; value: number | null; gap_after?: boolean }[];
  }[] = [];
  let granularityNote = "";

  if (payloads.length && resolvedMetrics.length) {
    const combos = payloads.flatMap((payload, pIndex) =>
      resolvedMetrics.map((metricId, mIndex) => ({
        payload,
        metricId,
        comboIndex: pIndex * resolvedMetrics.length + mIndex,
        metricIndex: mIndex,
      }))
    );
    const trends = await Promise.all(
      combos.map((c) =>
        api.playerTrend(c.payload.player.player_id, { metric: c.metricId, window: config.window }).catch(() => null)
      )
    );
    granularityNote = trends.find((t) => t)?.granularity_note ?? "";
    series = combos.flatMap((c, i) => {
      const trend = trends[i];
      if (!trend) return [];
      return [
        {
          label: `${c.payload.player.name} · ${meta!.metrics[c.metricId].name}`,
          color: OG_PLAYER_COLORS[c.comboIndex % OG_PLAYER_COLORS.length],
          dash: OG_METRIC_DASHES[c.metricIndex % OG_METRIC_DASHES.length],
          points: trend.points.map((p) => ({
            date: p.date,
            value: config.mode === "pct" ? p.pct : p.raw,
            gap_after: p.gap_after,
          })),
        },
      ];
    });
  }

  const title = payloads.length
    ? `Snapshot trend — ${payloads.map((p) => p.player.name).join(" vs ")}`
    : "Snapshot trend";
  const svg = trendChartSvg(series, {
    mode: config.mode,
    unit: "",
    title,
    granularityNote: granularityNote || "Snapshot granularity — dashed segments mark missing history",
  });

  const recency = payloads[0]?.raw.snapshot_date ?? null;
  return renderOgCard({
    title,
    subtitle: series.length
      ? `${series.length} line${series.length === 1 ? "" : "s"} · window of ${config.window} snapshots`
      : "Open the link to build a trend — this preview has nothing to draw yet.",
    chartSvg: svg,
    chartWidth: 860,
    chartHeight: 533,
    footer: ogFooter(
      config.mode === "pct" ? "Percentile view" : "Raw per-90 view",
      recency ? recency.slice(0, 10) : null
    ),
  });
}
