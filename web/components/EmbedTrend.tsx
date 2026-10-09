"use client";

import { useEffect, useMemo, useState } from "react";
import type { MetricMeta, PlayerPayload } from "@/lib/types";
import { TrendChart, type TrendMode } from "./TrendChart";
import { fetchTrendLines, type TrendLinesResult } from "@/lib/trend";
import { TREND_WINDOWS } from "@/lib/share";
import { formatDate } from "@/lib/format";

/**
 * Embeddable trend widget (Phase 3 — Part C3): the chart + attribution only.
 * Performance discipline matters inside third-party iframes — a single
 * resolved payload + one trend fetch per line, no extra chrome.
 */
export function EmbedTrend({
  slugs,
  metrics,
  window,
  mode,
  metricMeta,
}: {
  slugs: string[];
  metrics: string[];
  window: number;
  mode: TrendMode;
  metricMeta: Record<string, MetricMeta>;
}) {
  const [players, setPlayers] = useState<PlayerPayload[]>([]);
  const [result, setResult] = useState<TrendLinesResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const metricIds = metrics.filter((id) => metricMeta[id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all(
      slugs.slice(0, 3).map((slug) =>
        fetch(
          `${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/players/by-slug/${encodeURIComponent(slug)}`,
          { cache: "no-store" }
        ).then((res) => (res.ok ? (res.json() as Promise<PlayerPayload>) : null))
      )
    )
      .then((payloads) => {
        if (cancelled) return;
        const ok = payloads.filter((p): p is PlayerPayload => p !== null);
        setPlayers(ok);
        if (!ok.length) setError("No players could be resolved for this embed.");
        return ok;
      })
      .then((ok) => {
        if (!ok || !ok.length || cancelled) return;
        return fetchTrendLines({
          players: ok.map((p) => ({ id: p.player.player_id, name: p.player.name })),
          metrics: metricIds.map((id) => ({ id, meta: metricMeta[id] })),
          window: window || TREND_WINDOWS[0],
          mode,
        }).then((res) => {
          if (!cancelled) setResult(res);
        });
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "embed load failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slugs.join("|"), metricIds.join("|"), window, mode]);

  const recency = result?.payloads[0]?.points.at(-1)?.date;

  return (
    <div className="embed-widget">
      <TrendChart
        lines={result?.lines ?? []}
        events={result?.payloads[0]?.events ?? []}
        mode={mode}
        unit=""
        title="Snapshot trend"
        recency={recency ? formatDate(recency) : null}
        granularityNote={result?.granularityNote}
        loading={loading}
        error={error}
        emptyTitle="Nothing to plot"
        emptyBody="This embed references players or metrics that could not be resolved."
      />
      <p className="embed-widget__attribution">
        Powered by <a href="/" target="_top">Statlas</a> — analytics that shows its work
      </p>
    </div>
  );
}
