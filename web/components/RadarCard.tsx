"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Axis, PlayerPayload } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { RadarChart, type RadarMode, type RadarPlayer } from "./RadarChart";
import { buildRadarPlayers } from "@/lib/radar";
import { formatDate } from "@/lib/format";

export const MAX_PLAYERS = 4;

const STATUS_NOTE: Record<Axis["status"], string> = {
  qualified: "",
  below_floor: "below the metric's sample floor — shown as N/A, never a zero",
  unranked_pool: "value qualified but the position-group pool was below the minimum size for this metric",
  no_data: "no value for this metric in the latest snapshot",
};

type Props = {
  slugs: string[];
  title: string;
  subtitle?: string;
  maxPlayers?: number;
  /** Controlled mode (compare tool owns the toggle and the URL); omit for the
   * self-contained player-page card. */
  mode?: RadarMode;
  onModeChange?: (mode: RadarMode) => void;
};

export function RadarCard({ slugs, title, subtitle, maxPlayers = MAX_PLAYERS, mode: controlledMode, onModeChange }: Props) {
  const [payloads, setPayloads] = useState<PlayerPayload[]>([]);
  const [modeState, setModeState] = useState<RadarMode>("pct");
  const mode = controlledMode ?? modeState;
  const setMode = onModeChange ?? setModeState;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const capped = slugs.slice(0, maxPlayers);
  const limitExceeded = slugs.length > maxPlayers;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.allSettled(
        capped.map((slug) => api.playerBySlug(slug))
      );
      const ok: PlayerPayload[] = [];
      const failures: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "fulfilled") ok.push(result.value);
        else failures.push(capped[index]);
      });
      setPayloads(ok);
      if (!ok.length && failures.length) {
        setError(`Could not load ${failures.join(", ")}.`);
      } else if (failures.length) {
        setError(`Could not load ${failures.join(", ")} — showing the rest.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "query failed");
    } finally {
      setLoading(false);
    }
  }, [capped.join("|")]);

  useEffect(() => {
    if (capped.length) void load();
    else {
      setPayloads([]);
      setLoading(false);
    }
  }, [capped.join("|")]);

  const radarPlayers: RadarPlayer[] = useMemo(() => buildRadarPlayers(payloads), [payloads]);

  const insufficientNote = useMemo(() => {
    const notes = new Set<string>();
    for (const player of radarPlayers) {
      for (const axis of player.axes) {
        if (axis.status !== "qualified") {
          notes.add(`${axis.name} — ${STATUS_NOTE[axis.status]}`);
        }
      }
    }
    return notes.size ? `Insufficient data: ${Array.from(notes).join("; ")}.` : undefined;
  }, [radarPlayers]);

  const recency = payloads[0]?.percentiles.snapshot_date
    ? formatDate(payloads[0].percentiles.snapshot_date)
    : null;

  return (
    <div>
      <div className="radar-card__header" style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-lg) var(--radius-lg) 0 0", marginBottom: 0 }}>
        <div className="segmented" role="group" aria-label="Radar value scale">
          <button
            type="button"
            className="segmented__button"
            aria-pressed={mode === "pct"}
            onClick={() => setMode("pct")}
          >
            Percentile
          </button>
          <button
            type="button"
            className="segmented__button"
            aria-pressed={mode === "raw"}
            onClick={() => setMode("raw")}
          >
            Raw per-90
          </button>
        </div>
      </div>

      {limitExceeded && (
        <div className="state-block state-block--sunken" role="status" style={{ borderRadius: 0 }}>
          <p className="state-block__body">
            Comparison limit reached — the radar overlays up to {maxPlayers} players. Remove one
            before adding another (the 5th player is not plotted).
          </p>
        </div>
      )}

      <RadarChart
        players={radarPlayers}
        mode={mode}
        title={title}
        subtitle={subtitle}
        recency={recency}
        loading={loading}
        emptyTitle="No players selected yet"
        emptyBody={
          <>
            Use the search box to select a player and their percentile radar will appear here. You
            can overlay up to {maxPlayers} players — each is drawn with its own colour and named in
            the legend below the chart.
          </>
        }
        error={error}
        onRetry={() => void load()}
        insufficientNote={insufficientNote}
      />
    </div>
  );
}
