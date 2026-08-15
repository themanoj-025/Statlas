"use client";

import { useEffect, useState } from "react";
import type { PlayerPayload } from "@/lib/types";
import { RadarChart, type RadarMode, type RadarPlayer } from "./RadarChart";
import { buildRadarPlayers } from "@/lib/radar";
import { MAX_PLAYERS } from "./RadarCard";

/**
 * Embeddable radar widget (Phase 3 — Part C3). Renders ONLY the chart + a
 * "Powered by Statlas" attribution (the backlink mechanism); no chrome, no
 * toolbar, lazy-loaded by the host page via the iframe's loading attribute.
 */
export function EmbedRadar({
  slugs,
  mode,
}: {
  slugs: string[];
  mode: RadarMode;
}) {
  const [players, setPlayers] = useState<RadarPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const capped = slugs.slice(0, MAX_PLAYERS);
    setLoading(true);
    setError(null);
    Promise.all(
      capped.map((slug) =>
        fetch(
          `${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/players/by-slug/${encodeURIComponent(slug)}`,
          { cache: "no-store" }
        ).then((res) => (res.ok ? (res.json() as Promise<PlayerPayload>) : null))
      )
    )
      .then((payloads) => {
        if (cancelled) return;
        const ok = payloads.filter((p): p is PlayerPayload => p !== null);
        setPlayers(buildRadarPlayers(ok));
        if (!ok.length) setError("No players could be loaded for this embed.");
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
  }, [slugs.join("|")]);

  return (
    <div className="embed-widget">
      <RadarChart
        players={players}
        mode={mode}
        title="Player comparison"
        recency={null}
        loading={loading}
        error={error}
        emptyTitle="Nothing to plot"
        emptyBody="This embed references players that could not be resolved."
      />
      <p className="embed-widget__attribution">
        Powered by <a href="/" target="_top">Statlas</a> — analytics that shows its work
      </p>
    </div>
  );
}
