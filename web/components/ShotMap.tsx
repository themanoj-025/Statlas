"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EventMatch, ShotEvent } from "@/lib/types";
import { api } from "@/lib/api";
import { Pitch, soccerToPitch } from "./Pitch";
import { formatNumber } from "@/lib/format";

/**
 * Shot map (Phase 3 — Part B2). Rendered ONLY when the parent (EventMaps) has
 * confirmed coverage — this component never fetches outside the matrix.
 *
 * Outcome is encoded by shape AND colour (never colour alone): Goal = filled
 * circle, Saved = diamond, Blocked = triangle, Off Target = square. Shot size
 * scales with xG when the source provided it (null xG keeps a fixed size —
 * no invented precision). A data-table toggle is the screen-reader
 * alternative to the visual diagram (Part B2 a11y requirement).
 */

type OutcomeShape = "goal" | "saved" | "blocked" | "off_target" | "other";

const OUTCOME_COLORS: Record<OutcomeShape, string> = {
  goal: "var(--color-data-positive)",
  saved: "var(--cat-sky)",
  blocked: "var(--cat-vermillion)",
  off_target: "var(--color-text-disabled)",
  other: "var(--color-text-muted)",
};

const OUTCOME_LABELS: Record<OutcomeShape, string> = {
  goal: "Goal",
  saved: "Saved",
  blocked: "Blocked",
  off_target: "Off target",
  other: "Other outcome",
};

function classifyOutcome(outcome: string | null): OutcomeShape {
  const normalized = (outcome ?? "").toLowerCase();
  if (normalized.includes("goal")) return "goal";
  if (normalized.includes("save") || normalized.includes("post")) return "saved";
  if (normalized.includes("block")) return "blocked";
  if (normalized.includes("off")) return "off_target";
  return "other";
}

function ShotMarker({
  shot,
  shape,
  color,
  onHover,
}: {
  shot: ShotEvent;
  shape: OutcomeShape;
  color: string;
  onHover: (s: ShotEvent | null) => void;
}) {
  const pos = soccerToPitch(shot.x, shot.y);
  if (!pos) return null;
  // Size encodes xG where available; a null xG stays fixed (no false precision).
  const xg = shot.xg ?? 0.4;
  const r = 2.2 + 4.2 * Math.min(1, xg / 0.6);
  const common = {
    cx: pos.x,
    cy: pos.y,
    fill: color,
    stroke: "var(--color-surface-raised)",
    strokeWidth: 0.35,
    onMouseEnter: () => onHover(shot),
    onMouseLeave: () => onHover(null),
    onFocus: () => onHover(shot),
    onBlur: () => onHover(null),
    tabIndex: 0,
    className: "pitch-shot",
    style: { outline: "none" },
  } as const;
  switch (shape) {
    case "goal":
      return <circle r={r} {...common} />;
    case "saved":
      return (
        <path
          d={`M ${pos.x} ${pos.y - r} L ${pos.x + r * 0.7} ${pos.y} L ${pos.x} ${pos.y + r} L ${pos.x - r * 0.7} ${pos.y} Z`}
          fill={color}
          stroke="var(--color-surface-raised)"
          strokeWidth={0.35}
          onMouseEnter={() => onHover(shot)}
          onMouseLeave={() => onHover(null)}
          onFocus={() => onHover(shot)}
          onBlur={() => onHover(null)}
          tabIndex={0}
          className="pitch-shot"
          style={{ outline: "none" }}
        />
      );
    case "blocked":
      return (
        <path
          d={`M ${pos.x} ${pos.y - r} L ${pos.x + r} ${pos.y + r * 0.8} L ${pos.x - r} ${pos.y + r * 0.8} Z`}
          fill={color}
          stroke="var(--color-surface-raised)"
          strokeWidth={0.35}
          onMouseEnter={() => onHover(shot)}
          onMouseLeave={() => onHover(null)}
          onFocus={() => onHover(shot)}
          onBlur={() => onHover(null)}
          tabIndex={0}
          className="pitch-shot"
          style={{ outline: "none" }}
        />
      );
    case "off_target":
    case "other":
      return <rect x={pos.x - r * 0.8} y={pos.y - r * 0.8} width={r * 1.6} height={r * 1.6} {...common} />;
  }
}

export function ShotMap({
  playerId,
  playerName,
  competitions,
  matches,
  onLoadFilters,
}: {
  playerId: number;
  playerName: string;
  competitions: { competition_id: string; competition_name: string; season: string }[];
  matches: EventMatch[];
  onLoadFilters?: (filters: { competition?: string; season?: string }) => void;
}) {
  const [competition, setCompetition] = useState<string>(competitions[0]?.competition_id ?? "");
  const [season, setSeason] = useState<string>(competitions[0]?.season ?? "");
  const [match, setMatch] = useState<string>("");
  const [shots, setShots] = useState<ShotEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [tooltip, setTooltip] = useState<ShotEvent | null>(null);
  const [showTable, setShowTable] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const matchOptions = useMemo(
    () =>
      matches.filter(
        (m) =>
          (!competition || m.competition_id === competition) &&
          (!season || m.season === season)
      ),
    [matches, competition, season]
  );

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const data = await api.playerShots(
        playerId,
        {
          competition: competition || undefined,
          season: season || undefined,
          match: match || undefined,
        },
        { signal: controller.signal }
      );
      if (controller.signal.aborted) return;
      setShots(data);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "shot data query failed");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [playerId, competition, season, match, attempt]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  const counts = useMemo(() => {
    const byOutcome: Record<OutcomeShape, number> = { goal: 0, saved: 0, blocked: 0, off_target: 0, other: 0 };
    (shots ?? []).forEach((s) => {
      byOutcome[classifyOutcome(s.outcome)] += 1;
    });
    return byOutcome;
  }, [shots]);

  const describe = useMemo(() => {
    const total = shots?.length ?? 0;
    if (!total) return `Shot map for ${playerName} — no shots match the current filters.`;
    const goals = counts.goal;
    return `Shot map for ${playerName}: ${total} shots, ${goals} goal${goals === 1 ? "" : "s"}, ${counts.saved} saved, ${counts.blocked} blocked, ${counts.off_target} off target. Shot size encodes xG where available; outcome is shown by shape and colour.`;
  }, [playerName, shots, counts]);

  const tooltipPos = tooltip ? soccerToPitch(tooltip.x, tooltip.y) : null;

  return (
    <div className="map-card">
      <div className="toolbar" style={{ marginBottom: "var(--space-2)" }}>
        {competitions.length > 0 && (
          <>
            <div className="field" style={{ flex: "0 1 180px" }}>
              <label className="field__label" htmlFor="shot-competition">
                Competition
              </label>
              <select
                id="shot-competition"
                className="select"
                value={competition}
                onChange={(e) => {
                  const comp = competitions.find((c) => c.competition_id === e.target.value);
                  setCompetition(e.target.value);
                  if (comp) setSeason(comp.season);
                  setMatch("");
                }}
              >
                {competitions.map((comp) => (
                  <option key={`${comp.competition_id}-${comp.season}`} value={comp.competition_id}>
                    {comp.competition_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: "0 1 160px" }}>
              <label className="field__label" htmlFor="shot-season">
                Season
              </label>
              <select
                id="shot-season"
                className="select"
                value={season}
                onChange={(e) => {
                  setSeason(e.target.value);
                  setMatch("");
                }}
              >
                {competitions
                  .filter((c) => c.competition_id === competition)
                  .map((comp) => (
                    <option key={comp.season} value={comp.season}>
                      {comp.season}
                    </option>
                  ))}
              </select>
            </div>
          </>
        )}
        {matchOptions.length > 0 && (
          <div className="field" style={{ flex: "1 1 220px" }}>
            <label className="field__label" htmlFor="shot-match">
              Match
            </label>
            <select
              id="shot-match"
              className="select"
              value={match}
              onChange={(e) => setMatch(e.target.value)}
            >
              <option value="">All matches ({counts.goal + counts.saved + counts.blocked + counts.off_target + counts.other})</option>
              {matchOptions.map((m) => (
                <option key={m.match_id} value={m.match_id}>
                  {m.match_id}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="field" style={{ marginLeft: "auto" }}>
          <span className="field__label" aria-hidden="true">
            &nbsp;
          </span>
          <button
            type="button"
            className="button button--ghost button--sm"
            aria-expanded={showTable}
            onClick={() => setShowTable((open) => !open)}
          >
            {showTable ? "Hide data table" : "Show data table"}
          </button>
        </div>
      </div>

      {loading && (
        <div className="pitch-skeleton" role="status" aria-label="Loading shot map">
          <Pitch ariaLabel="Loading shot map">
            <rect className="pitch-skeleton__shimmer" x="70" y="20" width="22" height="10" rx="1" />
            <rect className="pitch-skeleton__shimmer" x="80" y="45" width="22" height="10" rx="1" />
            <rect className="pitch-skeleton__shimmer" x="75" y="62" width="22" height="10" rx="1" />
          </Pitch>
        </div>
      )}

      {!loading && error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__title">We couldn&rsquo;t load the shot map.</p>
          <p className="state-block__body">
            {error} The weekly data refresh is scheduled for Wednesday 03:00 UTC.
          </p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm" onClick={() => setAttempt((a) => a + 1)}>
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && !error && (shots?.length ?? 0) === 0 && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">No shots match these filters</p>
          <p className="state-block__body">
            This player has no shot events for the selected {match ? "match" : "competition/season"}.
            Change the filters above, or check the data coverage page for what event data exists.
          </p>
        </div>
      )}

      {!loading && !error && (shots?.length ?? 0) > 0 && (
        <>
          <div className="pitch-wrap">
            <Pitch ariaLabel={describe}>
              {shots!.map((shot) => (
                <ShotMarker
                  key={shot.event_id}
                  shot={shot}
                  shape={classifyOutcome(shot.outcome)}
                  color={OUTCOME_COLORS[classifyOutcome(shot.outcome)]}
                  onHover={setTooltip}
                />
              ))}
            </Pitch>

            {tooltip && tooltipPos && (
              <div
                className="radar-axis-tooltip"
                role="tooltip"
                style={{
                  left: `${(tooltipPos.x / 120) * 100}%`,
                  top: `${(tooltipPos.y / 80) * 100}%`,
                  transform: "translate(-50%, -115%)",
                }}
              >
                <div className="radar-axis-tooltip__name">{OUTCOME_LABELS[classifyOutcome(tooltip.outcome)]}</div>
                <div>
                  {tooltip.minute !== null ? `${Math.round(tooltip.minute)}'` : "minute unknown"}
                  {tooltip.xg !== null ? ` · xG ${formatNumber(tooltip.xg, 2)}` : ""}
                </div>
                <div style={{ color: "var(--color-text-muted)", marginTop: 4 }}>
                  {tooltip.body_part ?? "body part unknown"}
                </div>
              </div>
            )}
          </div>

          {/* legend: shape + colour + count — never colour alone */}
          <div className="map-legend" role="list" aria-label="Shot outcomes">
            {(Object.keys(OUTCOME_LABELS) as OutcomeShape[]).map((shape) => (
              <span key={shape} className="map-legend__item" role="listitem">
                <svg width="14" height="14" aria-hidden="true">
                  {shape === "goal" && <circle cx="7" cy="7" r="5.5" fill={OUTCOME_COLORS[shape]} />}
                  {shape === "saved" && <path d="M 7 1.5 L 12.5 7 L 7 12.5 L 1.5 7 Z" fill={OUTCOME_COLORS[shape]} />}
                  {shape === "blocked" && <path d="M 7 1.5 L 13 12 L 1 12 Z" fill={OUTCOME_COLORS[shape]} />}
                  {shape === "off_target" && <rect x="2" y="2" width="10" height="10" fill={OUTCOME_COLORS[shape]} />}
                  {shape === "other" && <rect x="2" y="2" width="10" height="10" fill={OUTCOME_COLORS[shape]} />}
                </svg>
                {OUTCOME_LABELS[shape]}
                <span className="num">· {counts[shape]}</span>
              </span>
            ))}
            <span className="map-legend__item" role="listitem">
              <span className="map-legend__size" aria-hidden="true" />
              Size = xG (larger = higher quality chance)
            </span>
          </div>

          {showTable && (
            <div className="table-wrap" style={{ marginTop: "var(--space-3)" }}>
              <table className="table" aria-label={`Shots for ${playerName}`}>
                <caption className="visually-hidden">
                  Structured shot data for {playerName} — the visual pitch diagram is not
                  accessible on its own.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Minute</th>
                    <th scope="col">Outcome</th>
                    <th scope="col">xG</th>
                    <th scope="col">Body part</th>
                    <th scope="col">X</th>
                    <th scope="col">Y</th>
                  </tr>
                </thead>
                <tbody>
                  {shots!.map((shot) => (
                    <tr key={shot.event_id}>
                      <td className="num">{shot.minute !== null ? Math.round(shot.minute) : "—"}</td>
                      <td>{shot.outcome ?? "—"}</td>
                      <td className="num">{shot.xg !== null ? formatNumber(shot.xg, 2) : "—"}</td>
                      <td>{shot.body_part ?? "—"}</td>
                      <td className="num">{shot.x !== null ? shot.x.toFixed(1) : "—"}</td>
                      <td className="num">{shot.y !== null ? shot.y.toFixed(1) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
