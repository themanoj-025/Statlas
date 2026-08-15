import type { TrendLineInput, TrendMode } from "@/components/TrendChart";
import type { MetricMeta, TrendPayload } from "./types";
import { metricDash, playerColor } from "./colors";
import { api } from "./api";

export type TrendSourcePlayer = { id: number; name: string };

export type TrendLinesResult = {
  lines: TrendLineInput[];
  payloads: TrendPayload[];
  insufficient: boolean;
  available: number;
  minSnapshots: number;
  granularityNote: string;
  window: number;
};

/**
 * Fetch one trend line per (player, metric) combination and map the payloads
 * to the chart's line format. One call per combination keeps the API contract
 * exactly as specified (`get_player_trend(player_id, metric, window)`) and lets
 * the tool overlay any players × metrics combination.
 */
export async function fetchTrendLines(params: {
  players: TrendSourcePlayer[];
  metrics: { id: string; meta: MetricMeta }[];
  window: number;
  mode: TrendMode;
  signal?: AbortSignal;
}): Promise<TrendLinesResult> {
  const { players, metrics, window, mode, signal } = params;
  const combos: { player: TrendSourcePlayer; metric: { id: string; meta: MetricMeta }; index: number }[] = [];
  players.forEach((player, pIndex) => {
    metrics.forEach((metric, mIndex) => {
      combos.push({ player, metric, index: pIndex * metrics.length + mIndex });
    });
  });

  const results = await Promise.all(
    combos.map((combo) =>
      api
        .playerTrend(combo.player.id, { metric: combo.metric.id, window }, signal ? { signal } : undefined)
        .then((payload): { combo: (typeof combos)[number]; payload: TrendPayload } => ({ combo, payload }))
    )
  );

  const lines: TrendLineInput[] = results.map(({ combo, payload }) => ({
    id: `${combo.player.id}-${combo.metric.id}`,
    label: `${combo.player.name} · ${combo.metric.meta.name}`,
    color: playerColor(combo.index),
    dash: metricDash(combo.index),
    points: payload.points.map((p) => ({
      date: p.date,
      value: mode === "pct" ? p.pct : p.raw,
      gap_after: p.gap_after,
      anomaly: p.anomaly,
    })),
  }));

  const payloads = results.map((r) => r.payload);
  const available = payloads.length ? Math.min(...payloads.map((p) => p.available)) : 0;
  const minSnapshots = payloads[0]?.min_snapshots ?? 5;
  const granularityNote = payloads[0]?.granularity_note ?? "";
  const insufficient = payloads.some((p) => p.insufficient) || !payloads.length;

  return { lines, payloads, insufficient, available, minSnapshots, granularityNote, window };
}
