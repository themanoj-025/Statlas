"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import type { MetricMeta, PlayerPayload, SearchResult } from "@/lib/types";
import { SearchCombobox } from "./SearchCombobox";
import { TrendChart, type TrendMode } from "./TrendChart";
import { SharePanel } from "./SharePanel";
import { fetchTrendLines, type TrendLinesResult } from "@/lib/trend";
import { formatDate } from "@/lib/format";
import {
  MAX_TREND_PLAYERS,
  TREND_WINDOWS,
  decodeTrendQuery,
  encodeTrendQuery,
  ogImageUrl,
  sharePageUrl,
} from "@/lib/share";

export type TrendToolInitial = {
  players: { slug: string }[];
  metrics: string[];
  window: number;
  mode: TrendMode;
};

const DEFAULT_METRICS = ["si_prgp_p90", "si_prgc_p90"];

/**
 * The /trend tool: up to MAX_TREND_PLAYERS players overlaid across multiple
 * metrics (line style per metric, colour per player), window + mode controls,
 * a stable shareable permalink, dynamic OG image and embed code.
 */
export function TrendTool({
  initial,
  metricMeta,
}: {
  initial: TrendToolInitial;
  metricMeta: Record<string, MetricMeta>;
}) {
  const router = useRouter();
  const [players, setPlayers] = useState<PlayerPayload[]>([]);
  const [metrics, setMetrics] = useState<string[]>(
    initial.metrics.length ? initial.metrics : [...DEFAULT_METRICS]
  );
  const [window, setWindow] = useState<number>(initial.window);
  const [mode, setMode] = useState<TrendMode>(initial.mode);
  const [result, setResult] = useState<TrendLinesResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const metricIds = metrics.filter((id) => metricMeta[id]);

  // Resolve the initial slugs to player payloads (the URL is the source of
  // truth on first paint; afterwards local state owns the URL).
  useEffect(() => {
    let cancelled = false;
    const slugs = initial.players.map((p) => p.slug);
    if (!slugs.length) {
      setLoading(false);
      return;
    }
    Promise.all(
      slugs.map((slug) =>
        fetch(
          `${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/players/by-slug/${encodeURIComponent(slug)}`,
          { cache: "no-store" }
        ).then((res) => (res.ok ? (res.json() as Promise<PlayerPayload>) : null))
      )
    )
      .then((payloads) => {
        if (cancelled) return;
        setPlayers(payloads.filter((p): p is PlayerPayload => p !== null));
      })
      .catch(() => {
        if (!cancelled) setError("Could not resolve the players in this link.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTrendLines({
        players: players.map((p) => ({ id: p.player.player_id, name: p.player.name })),
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
  }, [players, metricIds.join("|"), window, mode, attempt]);

  useEffect(() => {
    if (!players.length || !metricIds.length) {
      setResult(null);
      setLoading(false);
      return;
    }
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  // Keep the URL in sync — the shareable permalink reproduces this exact state.
  useEffect(() => {
    if (!players.length && !metrics.length) return;
    const query = encodeTrendQuery({
      players: players.map((p) => p.player.slug).filter((s): s is string => Boolean(s)),
      metrics,
      window,
      mode,
    });
    router.replace(query ? `/trend?${query}` : "/trend", { scroll: false });
  }, [players, metrics, window, mode, router]);

  const query = useMemo(
    () =>
      encodeTrendQuery({
        players: players.map((p) => p.player.slug).filter((s): s is string => Boolean(s)),
        metrics,
        window,
        mode,
      }),
    [players, metrics, window, mode]
  );

  const addPlayer = (result: SearchResult) => {
    if (!result.slug) return;
    if (players.length >= MAX_TREND_PLAYERS) return;
    fetch(`${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/players/by-slug/${encodeURIComponent(result.slug)}`, {
      cache: "no-store",
    })
      .then((res) => (res.ok ? (res.json() as Promise<PlayerPayload>) : null))
      .then((payload) => {
        if (payload) setPlayers((current) => [...current, payload].slice(0, MAX_TREND_PLAYERS));
      })
      .catch(() => setError("Could not load that player's trend."));
  };

  const removePlayer = (playerId: number) => {
    setPlayers((current) => current.filter((p) => p.player.player_id !== playerId));
  };

  const toggleMetric = (id: string) => {
    setMetrics((current) =>
      current.includes(id) ? current.filter((m) => m !== id) : [...current, id]
    );
  };

  const atLimit = players.length >= MAX_TREND_PLAYERS;
  const hasLines = result && result.lines.length > 0;

  return (
    <div>
      <div className="toolbar">
        <div className="field" style={{ flex: "1 1 300px" }}>
          <label className="field__label" htmlFor="trend-search">
            {players.length ? "Add another player" : "Search a player to start"}
          </label>
          <SearchCombobox onSelect={addPlayer} placeholder="e.g. 'Haaland' or 'Salah'" />
        </div>

        <div className="field">
          <span className="field__label" id="trend-metrics-label">
            Metrics
          </span>
          <div className="chip-group" role="group" aria-labelledby="trend-metrics-label">
            {Object.values(metricMeta).map((meta) => (
              <button
                key={meta.id}
                type="button"
                className={`chip ${metrics.includes(meta.id) ? "chip--primary" : ""}`}
                aria-pressed={metrics.includes(meta.id)}
                onClick={() => toggleMetric(meta.id)}
              >
                {meta.name}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label className="field__label" htmlFor="trend-window">
            Window
          </label>
          <select
            id="trend-window"
            className="select"
            style={{ minWidth: 120 }}
            value={window}
            onChange={(e) => setWindow(Number(e.target.value))}
          >
            {TREND_WINDOWS.map((w) => (
              <option key={w} value={w}>
                Last {w} snapshots
              </option>
            ))}
          </select>
        </div>

        {players.length > 0 && (
          <div className="field">
            <span className="field__label" aria-hidden="true">
              &nbsp;
            </span>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => {
                router.replace("/trend", { scroll: false });
                setPlayers([]);
              }}
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {players.length > 0 && (
        <div className="radar-legend" style={{ marginBottom: "var(--space-3)", gap: "var(--space-2)" }}>
          {players.map((player, index) => (
            <span key={player.player.player_id} className="chip" style={{ gap: "var(--space-2)" }}>
              <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 3, background: ["var(--cat-blue)", "var(--cat-vermillion)", "var(--cat-green)", "var(--cat-sky)"][index % 4] }} />
              {player.player.name}
              <button
                type="button"
                className="icon-button"
                style={{ width: 24, height: 24, border: "none", background: "transparent" }}
                aria-label={`Remove ${player.player.name}`}
                onClick={() => removePlayer(player.player.player_id)}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}

      {atLimit && (
        <div className="state-block state-block--sunken" role="status" style={{ marginBottom: "var(--space-3)" }}>
          <p className="state-block__body">
            The trend overlays up to {MAX_TREND_PLAYERS} players. Remove one before adding another.
          </p>
        </div>
      )}

      <TrendChart
        lines={result?.lines ?? []}
        events={result?.payloads[0]?.events ?? []}
        mode={mode}
        unit=""
        title="Snapshot history — trend"
        subtitle="One line per player × metric. Solid lines are consecutive snapshots; dashed segments mark missing snapshot history — never interpolated."
        recency={result?.payloads[0]?.points.at(-1)?.date ? formatDate(result.payloads[0].points.at(-1)!.date) : null}
        granularityNote={result?.granularityNote}
        loading={loading}
        error={error}
        onRetry={() => setAttempt((a) => a + 1)}
        emptyTitle="No players or metrics selected"
        emptyBody={
          <>
            Use the search box to add up to {MAX_TREND_PLAYERS} players and pick at least one
            metric — each combination draws its own line, named in the legend below the chart.
          </>
        }
      />

      {hasLines && query && (
        <div style={{ marginTop: "var(--space-4)" }}>
          <SharePanel
            kind="trend"
            query={query}
            title="Statlas trend comparison"
            shareTitle="Snapshot trend comparison on Statlas"
          />
        </div>
      )}
    </div>
  );
}
