"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { RadarCard, MAX_PLAYERS } from "@/components/RadarCard";
import { SearchCombobox } from "@/components/SearchCombobox";
import { SharePanel } from "@/components/SharePanel";
import type { SearchResult } from "@/lib/types";
import { playerColor } from "@/lib/colors";
import {
  decodeRadarQuery,
  encodeRadarQuery,
  MAX_RADAR_PLAYERS,
} from "@/lib/share";

export type CompareToolInitial = {
  players: string[];
  mode: "pct" | "raw";
};

/**
 * The /compare tool: up to MAX_RADAR_PLAYERS overlaid radars. The URL is the
 * shareable permalink — it encodes the exact chart state (players + mode), and
 * the SharePanel exposes the OG-image preview + embed code for that state.
 */
export function CompareTool({ initial }: { initial: CompareToolInitial }) {
  const router = useRouter();
  const [players, setPlayers] = useState<SearchResult[] | null>(null);
  const [mode, setMode] = useState<"pct" | "raw">(initial.mode);

  const slugs =
    players?.map((p) => p.slug).filter((s): s is string => Boolean(s)) ?? initial.players;

  const addPlayer = (result: SearchResult) => {
    if (!result.slug) return;
    if (players && players.length >= MAX_PLAYERS) return;
    setPlayers((current) => {
      const next = [...(current ?? []), result].slice(0, MAX_PLAYERS);
      const newSlugs = next.map((p) => p.slug).filter(Boolean).join(",");
      router.replace(newSlugs ? `/compare?players=${newSlugs}&mode=${mode}` : "/compare", { scroll: false });
      return next;
    });
  };

  const removePlayer = (playerId: number) => {
    setPlayers((current) => {
      const next = (current ?? []).filter((p) => p.player_id !== playerId);
      const newSlugs = next.map((p) => p.slug).filter(Boolean).join(",");
      router.replace(newSlugs ? `/compare?players=${newSlugs}&mode=${mode}` : "/compare", { scroll: false });
      return next;
    });
  };

  const changeMode = (next: "pct" | "raw") => {
    setMode(next);
    if (slugs.length) {
      const query = encodeRadarQuery({ players: slugs, mode: next });
      router.replace(`/compare?${query}`, { scroll: false });
    }
  };

  const query = useMemo(
    () => encodeRadarQuery({ players: slugs, mode }),
    [slugs, mode]
  );
  const atLimit = slugs.length >= MAX_RADAR_PLAYERS;

  return (
    <div className="container page">
      <h1 className="page__title">Compare</h1>
      <p className="page__lede">
        Overlay up to {MAX_RADAR_PLAYERS} players&rsquo; radars on a single chart. Toggle between
        percentile view and raw per-90 view — every axis is labelled with its metric and unit, and
        values are never conveyed by colour alone.
      </p>

      <div className="toolbar">
        <div className="field" style={{ flex: "1 1 340px" }}>
          <label className="field__label" htmlFor="compare-search">
            {slugs.length ? "Add another player" : "Search a player to start"}
          </label>
          <SearchCombobox onSelect={addPlayer} autoFocus={!slugs.length} placeholder="e.g. 'Haaland' or 'Salah'" />
        </div>
        <div className="field">
          <span className="field__label" id="compare-mode-label">
            Scale
          </span>
          <div className="segmented" role="group" aria-labelledby="compare-mode-label">
            <button type="button" className="segmented__button" aria-pressed={mode === "pct"} onClick={() => changeMode("pct")}>
              Percentile
            </button>
            <button type="button" className="segmented__button" aria-pressed={mode === "raw"} onClick={() => changeMode("raw")}>
              Raw per-90
            </button>
          </div>
        </div>
        {slugs.length > 0 && (
          <div className="field">
            <span className="field__label" aria-hidden="true">
              &nbsp;
            </span>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => {
                router.replace("/compare", { scroll: false });
                setPlayers([]);
              }}
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {slugs.length > 0 && (
        <div className="radar-legend" style={{ marginBottom: "var(--space-3)", gap: "var(--space-2)" }}>
          {slugs.map((slug, index) => (
            <span key={slug} className="chip" style={{ gap: "var(--space-2)" }}>
              <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 3, background: playerColor(index) }} />
              {slug.replace(/-/g, " ")}
              <button
                type="button"
                className="icon-button"
                style={{ width: 24, height: 24, border: "none", background: "transparent" }}
                aria-label={`Remove ${slug}`}
                onClick={() => {
                  const name = players?.find((p) => p.slug === slug)?.player_id;
                  if (name) removePlayer(name);
                }}
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
            Comparison limit reached — the radar overlays up to {MAX_RADAR_PLAYERS} players. Remove
            one before adding another.
          </p>
        </div>
      )}

      <RadarCard
        slugs={slugs}
        title="Player comparison"
        subtitle="Percentile view: all axes share the 0–100 scale. Raw view: each axis scales to the highest displayed value."
        maxPlayers={MAX_RADAR_PLAYERS}
      />

      {slugs.length > 0 && (
        <div style={{ marginTop: "var(--space-4)" }}>
          <SharePanel
            kind="radar"
            query={query}
            title="Statlas player comparison"
            shareTitle="Player comparison radar on Statlas"
          />
        </div>
      )}
    </div>
  );
}
