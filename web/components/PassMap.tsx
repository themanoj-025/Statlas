"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EventMatch, PassEvent } from "@/lib/types";
import { api } from "@/lib/api";
import { Pitch, soccerToPitch } from "./Pitch";
import { formatNumber } from "@/lib/format";

/**
 * Pass map (Phase 3 — Part B3). Rendered ONLY when the parent (EventMaps) has
 * confirmed coverage. Every pass is a directional arrow (origin → end) with an
 * arrowhead — never an ambiguous line. Completion is colour + dash (solid =
 * completed, dashed = incomplete); progressive passes are thicker with a
 * larger arrowhead and can be isolated with the filter. The data-table toggle
 * is the screen-reader alternative (same requirement as the shot map).
 */

type PassFilter = "all" | "complete" | "incomplete";

export function PassMap({
  playerId,
  playerName,
  competitions,
  matches,
}: {
  playerId: number;
  playerName: string;
  competitions: { competition_id: string; competition_name: string; season: string }[];
  matches: EventMatch[];
}) {
  const [competition, setCompetition] = useState<string>(competitions[0]?.competition_id ?? "");
  const [season, setSeason] = useState<string>(competitions[0]?.season ?? "");
  const [match, setMatch] = useState<string>("");
  const [completion, setCompletion] = useState<PassFilter>("all");
  const [progressiveOnly, setProgressiveOnly] = useState(false);
  const [passes, setPasses] = useState<PassEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [tooltip, setTooltip] = useState<PassEvent | null>(null);
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
      const data = await api.playerPasses(
        playerId,
        {
          competition: competition || undefined,
          season: season || undefined,
          match: match || undefined,
        },
        { signal: controller.signal }
      );
      if (controller.signal.aborted) return;
      setPasses(data);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "pass data query failed");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [playerId, competition, season, match, attempt]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  const visible = useMemo(() => {
    const base = passes ?? [];
    const byCompletion = base.filter((p) => {
      if (completion === "complete") return p.outcome === "Complete";
      if (completion === "incomplete") return p.outcome === "Incomplete";
      return true;
    });
    return progressiveOnly ? byCompletion.filter((p) => p.progressive) : byCompletion;
  }, [passes, completion, progressiveOnly]);

  const counts = useMemo(() => {
    const completed = passes?.filter((p) => p.outcome === "Complete").length ?? 0;
    const progressive = passes?.filter((p) => p.progressive).length ?? 0;
    return { completed, incomplete: (passes?.length ?? 0) - completed, progressive };
  }, [passes]);

  const describe = useMemo(() => {
    if (!passes?.length) return `Pass map for ${playerName} — no passes match the current filters.`;
    return `Pass map for ${playerName}: ${counts.completed} completed and ${counts.incomplete} incomplete passes, ${counts.progressive} progressive. Arrows point from origin to destination; dashed arrows are incomplete passes; thicker arrows are progressive.`;
  }, [playerName, passes, counts]);

  const tooltipPos = tooltip ? soccerToPitch(tooltip.x, tooltip.y) : null;

  return (
    <div className="map-card">
      <div className="toolbar" style={{ marginBottom: "var(--space-2)" }}>
        {competitions.length > 0 && (
          <>
            <div className="field" style={{ flex: "0 1 180px" }}>
              <label className="field__label" htmlFor="pass-competition">
                Competition
              </label>
              <select
                id="pass-competition"
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
              <label className="field__label" htmlFor="pass-season">
                Season
              </label>
              <select
                id="pass-season"
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
          <div className="field" style={{ flex: "1 1 200px" }}>
            <label className="field__label" htmlFor="pass-match">
              Match
            </label>
            <select id="pass-match" className="select" value={match} onChange={(e) => setMatch(e.target.value)}>
              <option value="">All matches</option>
              {matchOptions.map((m) => (
                <option key={m.match_id} value={m.match_id}>
                  {m.match_id}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="field">
          <span className="field__label" id="pass-outcome-label">
            Outcome
          </span>
          <div className="segmented" role="group" aria-labelledby="pass-outcome-label">
            {(["all", "complete", "incomplete"] as PassFilter[]).map((f) => (
              <button
                key={f}
                type="button"
                className="segmented__button"
                aria-pressed={completion === f}
                onClick={() => setCompletion(f)}
              >
                {f === "all" ? "All" : f === "complete" ? "Completed" : "Incomplete"}
              </button>
            ))}
          </div>
        </div>
        <div className="field" style={{ marginLeft: "auto" }}>
          <span className="field__label" aria-hidden="true">
            &nbsp;
          </span>
          <button
            type="button"
            className={`button button--sm button--secondary ${progressiveOnly ? "button--active" : ""}`}
            aria-pressed={progressiveOnly}
            onClick={() => setProgressiveOnly((v) => !v)}
          >
            Progressive only
          </button>
        </div>
      </div>

      {loading && (
        <div className="pitch-skeleton" role="status" aria-label="Loading pass map">
          <Pitch ariaLabel="Loading pass map">
            <rect className="pitch-skeleton__shimmer" x="40" y="25" width="30" height="8" rx="1" />
            <rect className="pitch-skeleton__shimmer" x="60" y="50" width="30" height="8" rx="1" />
            <rect className="pitch-skeleton__shimmer" x="35" y="60" width="30" height="8" rx="1" />
          </Pitch>
        </div>
      )}

      {!loading && error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__title">We couldn&rsquo;t load the pass map.</p>
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

      {!loading && !error && visible.length === 0 && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">No passes match these filters</p>
          <p className="state-block__body">
            This player has no pass events for the current selection. Change the filters above, or
            check the data coverage page for what event data exists.
          </p>
        </div>
      )}

      {!loading && !error && visible.length > 0 && (
        <>
          <div className="pitch-wrap">
            <Pitch ariaLabel={describe}>
              <defs>
                <marker
                  id="pass-arrow-complete"
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="4"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L8,4 L0,8 Z" fill="var(--cat-green)" />
                </marker>
                <marker
                  id="pass-arrow-incomplete"
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="4"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L8,4 L0,8 Z" fill="var(--color-danger)" />
                </marker>
              </defs>
              {visible.map((pass) => {
                const origin = soccerToPitch(pass.x, pass.y);
                const end = soccerToPitch(pass.end_x, pass.end_y);
                if (!origin || !end) return null;
                const completed = pass.outcome === "Complete";
                const color = completed ? "var(--cat-green)" : "var(--color-danger)";
                const markerId = completed ? "pass-arrow-complete" : "pass-arrow-incomplete";
                return (
                  <line
                    key={pass.event_id}
                    className="pitch-pass"
                    x1={origin.x}
                    y1={origin.y}
                    x2={end.x}
                    y2={end.y}
                    stroke={color}
                    strokeWidth={pass.progressive ? 1 : 0.45}
                    strokeDasharray={completed ? undefined : "2 1.6"}
                    markerEnd={`url(#${markerId})`}
                    onMouseEnter={() => setTooltip(pass)}
                    onMouseLeave={() => setTooltip(null)}
                    onFocus={() => setTooltip(pass)}
                    onBlur={() => setTooltip(null)}
                    tabIndex={0}
                    style={{ outline: "none" }}
                  />
                );
              })}
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
                <div className="radar-axis-tooltip__name">
                  {tooltip.outcome ?? "Pass"}
                  {tooltip.progressive ? " · progressive" : ""}
                </div>
                <div>
                  {tooltip.minute !== null ? `${Math.round(tooltip.minute)}'` : "minute unknown"}
                  {tooltip.length !== null ? ` · ${formatNumber(tooltip.length, 0)} yd` : ""}
                </div>
                <div style={{ color: "var(--color-text-muted)", marginTop: 4 }}>
                  {tooltip.recipient ? `to ${tooltip.recipient}` : tooltip.pass_type ?? "pass type unknown"}
                </div>
              </div>
            )}
          </div>

          <div className="map-legend" role="list" aria-label="Pass legend">
            <span className="map-legend__item" role="listitem">
              <svg width="22" height="8" aria-hidden="true">
                <line x1="0" y1="4" x2="22" y2="4" stroke="var(--cat-green)" strokeWidth="3" />
              </svg>
              Completed · {counts.completed}
            </span>
            <span className="map-legend__item" role="listitem">
              <svg width="22" height="8" aria-hidden="true">
                <line x1="0" y1="4" x2="22" y2="4" stroke="var(--color-danger)" strokeWidth="3" strokeDasharray="2 2" />
              </svg>
              Incomplete · {counts.incomplete}
            </span>
            <span className="map-legend__item" role="listitem">
              <svg width="22" height="8" aria-hidden="true">
                <line x1="0" y1="4" x2="22" y2="4" stroke="var(--color-accent)" strokeWidth="5" />
              </svg>
              Progressive · {counts.progressive}
            </span>
            <span className="map-legend__item" role="listitem">
              Arrows point from origin to destination
            </span>
            <span style={{ marginLeft: "auto" }}>
              <button
                type="button"
                className="button button--ghost button--sm"
                aria-expanded={showTable}
                onClick={() => setShowTable((open) => !open)}
              >
                {showTable ? "Hide data table" : "Show data table"}
              </button>
            </span>
          </div>

          {showTable && (
            <div className="table-wrap" style={{ marginTop: "var(--space-3)" }}>
              <table className="table" aria-label={`Passes for ${playerName}`}>
                <caption className="visually-hidden">
                  Structured pass data for {playerName} — the visual pitch diagram is not
                  accessible on its own.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Minute</th>
                    <th scope="col">Outcome</th>
                    <th scope="col">Progressive</th>
                    <th scope="col">From X</th>
                    <th scope="col">From Y</th>
                    <th scope="col">To X</th>
                    <th scope="col">To Y</th>
                    <th scope="col">Length</th>
                    <th scope="col">Recipient</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((pass) => (
                    <tr key={pass.event_id}>
                      <td className="num">{pass.minute !== null ? Math.round(pass.minute) : "—"}</td>
                      <td>{pass.outcome ?? "—"}</td>
                      <td>{pass.progressive ? "yes" : "no"}</td>
                      <td className="num">{pass.x !== null ? pass.x.toFixed(1) : "—"}</td>
                      <td className="num">{pass.y !== null ? pass.y.toFixed(1) : "—"}</td>
                      <td className="num">{pass.end_x !== null ? pass.end_x.toFixed(1) : "—"}</td>
                      <td className="num">{pass.end_y !== null ? pass.end_y.toFixed(1) : "—"}</td>
                      <td className="num">{pass.length !== null ? formatNumber(pass.length, 0) : "—"}</td>
                      <td>{pass.recipient ?? "—"}</td>
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
