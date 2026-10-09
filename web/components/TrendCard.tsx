"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MetricMeta } from "@/lib/types";
import { TrendChart, type TrendMode } from "./TrendChart";
import { DEFAULT_TREND_METRICS, TREND_WINDOWS } from "@/lib/share";
import { fetchTrendLines, type TrendLinesResult } from "@/lib/trend";
import { formatDate, formatNumber } from "@/lib/format";

type Props = {
  playerId: number;
  playerName: string;
  playerSlug: string;
  metrics?: string[];
  metricMeta: Record<string, MetricMeta>;
  window?: number;
  mode?: TrendMode;
  title?: string;
  subtitle?: string;
  compact?: boolean; // embed / player-page layout tweaks
};

/**
 * One player's snapshot-history trend. The honest insufficient-history state
 * is the Phase 3 empty-state contract: "X of N minimum snapshots available —
 * trend will appear as more data is collected" (a young dataset states its
 * own limitation instead of hiding it).
 */
export function TrendCard({
  playerId,
  playerName,
  playerSlug,
  metrics = [...DEFAULT_TREND_METRICS],
  metricMeta,
  window = TREND_WINDOWS[0],
  mode: initialMode = "raw",
  title,
  subtitle,
}: Props) {
  const [mode, setMode] = useState<TrendMode>(initialMode);
  const [result, setResult] = useState<TrendLinesResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const metricIds = metrics.filter((id) => metricMeta[id]);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTrendLines({
        players: [{ id: playerId, name: playerName }],
        metrics: metricIds.map((id) => ({ id, meta: metricMeta[id] })),
        window,
        mode,
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setResult(result);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "trend query failed");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [playerId, playerName, metricIds.join("|"), window, mode, attempt]);

  useEffect(() => {
    if (!metricIds.length) {
      setLoading(false);
      return;
    }
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  const hasPoints = (result?.lines ?? []).some((l) => l.points.some((p) => p.value !== null));

  return (
    <div>
      <div className="radar-card__header" style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg) var(--radius-lg) 0 0", marginBottom: 0 }}>
        <div className="segmented" role="group" aria-label="Trend value scale">
          <button type="button" className="segmented__button" aria-pressed={mode === "pct"} onClick={() => setMode("pct")}>
            Percentile
          </button>
          <button type="button" className="segmented__button" aria-pressed={mode === "raw"} onClick={() => setMode("raw")}>
            Raw per-90
          </button>
        </div>
      </div>

      {result?.insufficient && !loading && !error && (
        <div className="state-block state-block--sunken" role="status" style={{ borderRadius: 0, borderTop: "none" }}>
          <p className="state-block__title">Not enough snapshot history yet</p>
          <p className="state-block__body">
            {result.available} of {result.minSnapshots} minimum snapshots available for{" "}
            {playerName} — the trend will appear as more data is collected. Snapshot history is
            append-only and grows with each weekly refresh (Wednesday 03:00 UTC).
          </p>
          {hasPoints && (
            <div className="trend-insufficient-table">
              <table className="table" aria-label={`Available snapshots for ${playerName}`}>
                <thead>
                  <tr>
                    <th scope="col">Snapshot date</th>
                    {metricIds.map((id) => (
                      <th key={id} scope="col" className="num">
                        {metricMeta[id].name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.payloads[0]?.points.map((point) => (
                    <tr key={point.date}>
                      <td>{formatDate(point.date)}</td>
                      {metricIds.map((id) => {
                        const payload = result.payloads.find((p) => p.metric.id === id);
                        const p = payload?.points.find((pp) => pp.date === point.date);
                        return (
                          <td key={id} className="num">
                            {p?.raw !== null && p?.raw !== undefined ? formatNumber(p.raw, 2) : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <TrendChart
        lines={result?.lines ?? []}
        events={result?.payloads[0]?.events ?? []}
        mode={mode}
        unit=""
        title={title ?? `Snapshot history — ${playerName}`}
        subtitle={subtitle}
        recency={result?.payloads[0]?.points.at(-1)?.date ? formatDate(result.payloads[0].points.at(-1)!.date) : null}
        granularityNote={result?.granularityNote}
        loading={loading}
        error={error}
        onRetry={() => setAttempt((a) => a + 1)}
        emptyTitle="No snapshot history yet"
        emptyBody={
          <>
            No versioned snapshots exist for {playerName} yet. The first snapshot is written by the
            weekly refresh (Wednesday 03:00 UTC) — the trend appears once at least{" "}
            {result?.minSnapshots ?? 5} snapshots have accumulated.
          </>
        }
      />
    </div>
  );
}
