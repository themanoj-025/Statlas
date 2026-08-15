"use client";

import { useId, useMemo } from "react";
import { formatNumber } from "@/lib/format";

/**
 * Trend / time-series chart (Phase 3 — Part A2).
 *
 * Renders snapshot-history lines (one per player × metric) with the honesty
 * rules baked in:
 * - gaps are DASHED segments with an explicit break marker — never a false
 *   smooth line through missing data (Part D quality gate);
 * - flagged snapshots (unresolved anomalies) get a warning ring;
 * - derived transfer events are annotated on the timeline;
 * - every value has a numeric label; colour is never the only signal.
 *
 * Pure presentation: data arrives via props (TrendCard / TrendTool / embed).
 */

export type TrendPointInput = {
  date: string;
  value: number | null;
  gap_after?: boolean;
  anomaly?: boolean;
};

export type TrendLineInput = {
  id: string;
  label: string; // "Erling Haaland · Goals per 90"
  color: string; // CSS token (player colour)
  dash: string; // SVG stroke-dasharray for the metric ("" = solid)
  points: TrendPointInput[];
};

export type TrendEventInput = {
  date: string;
  type: "transfer";
  team_from: string | null;
  team_to: string | null;
};

export type TrendMode = "pct" | "raw";

export const METRIC_DASHES = ["", "8 6", "2 6"] as const;

const W = 820;
const H = 440;
const PAD_L = 62;
const PAD_R = 26;
const PAD_T = 18;
const PAD_B = 46;
const PLOT_W = W - PAD_L - PAD_R;
const PLOT_H = H - PAD_T - PAD_B;

function describeTrend(lines: TrendLineInput[], mode: TrendMode): string {
  if (!lines.length) return "No trend lines selected.";
  const parts = lines.map((line) => {
    const values = line.points
      .map((p) => p.value)
      .filter((v): v is number => v !== null);
    if (!values.length) return `${line.label}: no values yet.`;
    const first = values[0];
    const last = values[values.length - 1];
    const direction = last > first ? "rising" : last < first ? "falling" : "steady";
    return `${line.label}: ${mode === "pct" ? `${Math.round(last)}th percentile` : formatNumber(last, 2)} on the latest snapshot, ${direction} over the window.`;
  });
  return `Line chart of snapshot history. ${parts.join(" ")}`;
}

export function TrendChart({
  lines,
  events,
  mode,
  unit,
  title,
  subtitle,
  recency,
  granularityNote,
  loading = false,
  emptyTitle = "No trend to draw yet",
  emptyBody,
  error,
  onRetry,
}: {
  lines: TrendLineInput[];
  events?: TrendEventInput[];
  mode: TrendMode;
  unit: string;
  title: string;
  subtitle?: string;
  recency?: string | null;
  granularityNote?: string;
  loading?: boolean;
  emptyTitle?: string;
  emptyBody?: React.ReactNode;
  error?: string | null;
  onRetry?: () => void;
}) {
  const uid = useId().replace(/:/g, "");

  const geometry = useMemo(() => {
    const dates = Array.from(
      new Set(lines.flatMap((l) => l.points.map((p) => p.date)))
    ).sort();
    const allValues = lines.flatMap((l) =>
      l.points.map((p) => p.value).filter((v): v is number => v !== null)
    );
    const yMax = mode === "pct" ? 100 : Math.max(0, ...allValues) * 1.15 || 1;
    const xFor = (date: string) =>
      PAD_L + (dates.length <= 1 ? PLOT_W / 2 : (dates.indexOf(date) / (dates.length - 1)) * PLOT_W);
    const yFor = (value: number) => PAD_T + PLOT_H - (value / yMax) * PLOT_H;
    return { dates, yMax, xFor, yFor };
  }, [lines, mode]);

  const { dates, yMax, xFor, yFor } = geometry;

  // ---- loading skeleton: an actual line-chart shape, not a gray box ------
  if (loading) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="trend-skeleton" role="status" aria-label={`Loading trend for ${title}`}>
            <svg viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
              {[0.25, 0.5, 0.75, 1].map((frac) => (
                <line
                  key={frac}
                  className="trend-grid"
                  x1={PAD_L}
                  x2={W - PAD_R}
                  y1={PAD_T + PLOT_H * frac}
                  y2={PAD_T + PLOT_H * frac}
                />
              ))}
              <path className="trend-skeleton-line" d={`M${PAD_L},${PAD_T + PLOT_H * 0.8} L${PAD_L + PLOT_W * 0.3},${PAD_T + PLOT_H * 0.55} L${PAD_L + PLOT_W * 0.6},${PAD_T + PLOT_H * 0.62} L${W - PAD_R},${PAD_T + PLOT_H * 0.3}`} />
              <path className="trend-skeleton-line" d={`M${PAD_L},${PAD_T + PLOT_H * 0.7} L${PAD_L + PLOT_W * 0.4},${PAD_T + PLOT_H * 0.45} L${W - PAD_R},${PAD_T + PLOT_H * 0.5}`} />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  // ---- error --------------------------------------------------------------
  if (error) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="state-block state-block--error" role="alert">
            <p className="state-block__title">We couldn&rsquo;t load the trend.</p>
            <p className="state-block__body">
              {error} The weekly data refresh is scheduled for Wednesday 03:00 UTC — if this
              persists after refresh, tell us at data@statlas.com.
            </p>
            <div className="state-block__actions">
              {onRetry && (
                <button type="button" className="button button--sm" onClick={onRetry}>
                  Retry
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---- empty / insufficient history ---------------------------------------
  const drawable = lines.some((l) => l.points.some((p) => p.value !== null));
  if (!drawable) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__title">{emptyTitle}</p>
            <p className="state-block__body">{emptyBody}</p>
          </div>
        </div>
      </div>
    );
  }

  const aria = describeTrend(lines, mode);
  const step = yMax / 4;
  const ticks = [0, 1, 2, 3, 4].map((i) => i * step);

  return (
    <div className="radar-card">
      <div className="radar-card__header">
        <div>
          <h2 className="radar-card__title">{title}</h2>
          {subtitle && (
            <p style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
              {subtitle}
            </p>
          )}
        </div>
        {recency && <span className="recency">Data as of {recency}</span>}
      </div>

      <div className="radar-card__body">
        <div className="trend-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} className="trend-svg" role="img" aria-label={aria}>
            {/* gridlines + y labels (tabular, data family) */}
            {ticks.map((tick) => {
              const y = yFor(tick);
              const label = mode === "pct" ? String(Math.round(tick)) : formatNumber(tick, 1);
              return (
                <g key={tick}>
                  <line className={tick === 0 ? "trend-zero" : "trend-grid"} x1={PAD_L} x2={W - PAD_R} y1={y} y2={y} />
                  <text className="trend-axis-label" x={PAD_L - 8} y={y + 4} textAnchor="end">
                    {label}
                  </text>
                </g>
              );
            })}

            {/* x labels: first / middle / last date */}
            {[0, Math.floor((dates.length - 1) / 2), dates.length - 1].map((i) => {
              if (i < 0 || i >= dates.length) return null;
              return (
                <text
                  key={`${uid}-x-${i}`}
                  className="trend-axis-label"
                  x={xFor(dates[i])}
                  y={H - PAD_B + 26}
                  textAnchor="middle"
                >
                  {dates[i].slice(0, 10)}
                </text>
              );
            })}

            {/* transfer annotations — derived from real team_id changes */}
            {events?.map((event, i) => {
              const x = xFor(event.date);
              return (
                <g key={`${uid}-evt-${i}`} className="trend-transfer">
                  <line x1={x} x2={x} y1={PAD_T} y2={PAD_T + PLOT_H} />
                  <circle cx={x} cy={PAD_T + 10} r={9} />
                  <text x={x} y={PAD_T + 15} textAnchor="middle" className="trend-transfer-mark">
                    ⇄
                  </text>
                </g>
              );
            })}

            {/* lines */}
            {lines.map((line) => {
              const pts = line.points.filter((p) => p.value !== null) as { date: string; value: number; gap_after?: boolean; anomaly?: boolean }[];
              if (!pts.length) return null;

              // Build solid path + dashed gap segments + break markers.
              const solid: string[] = [];
              const dashed: { d: string; x: number }[] = [];
              let current: string[] = [];
              pts.forEach((p, i) => {
                const x = xFor(p.date);
                current.push(`${x.toFixed(1)},${yFor(p.value).toFixed(1)}`);
                if (p.gap_after && i + 1 < pts.length) {
                  const nextX = xFor(pts[i + 1].date);
                  dashed.push({
                    d: `M${current.join(" L")} L${nextX.toFixed(1)},${yFor(pts[i + 1].value).toFixed(1)}`,
                    x: (x + nextX) / 2,
                  });
                  current = [];
                }
              });
              if (current.length) solid.push(`M${current.join(" L")}`);

              const area =
                pts.length > 1
                  ? `${solid[0] ?? dashed[0]?.d ?? ""} L${xFor(pts[pts.length - 1].date).toFixed(1)},${PAD_T + PLOT_H} L${xFor(pts[0].date).toFixed(1)},${PAD_T + PLOT_H} Z`
                  : "";

              return (
                <g key={line.id}>
                  {area && <path d={area} fill={line.color} fillOpacity={0.1} stroke="none" />}
                  {dashed.map((seg, i) => (
                    <g key={`${line.id}-gap-${i}`}>
                      <path d={seg.d} className="trend-line trend-line--gap" stroke={line.color} strokeDasharray="3 7" />
                      {/* explicit break marker: never a silent interpolation */}
                      <line
                        x1={seg.x}
                        x2={seg.x}
                        y1={yFor(pts[0].value)}
                        y2={yFor(pts[0].value) + 26}
                        className="trend-gap-marker"
                      />
                      <text x={seg.x} y={yFor(pts[0].value) + 40} textAnchor="middle" className="trend-gap-label">
                        gap
                      </text>
                    </g>
                  ))}
                  {solid.map((d, i) => (
                    <path key={i} d={d} className="trend-line" stroke={line.color} strokeDasharray={line.dash} />
                  ))}
                  {pts.map((p, i) => (
                    <g key={`${line.id}-pt-${i}`}>
                      <circle cx={xFor(p.date)} cy={yFor(p.value)} r={4.5} fill={line.color} stroke="var(--color-surface-raised)" strokeWidth={1.5} />
                      {p.anomaly && (
                        <circle cx={xFor(p.date)} cy={yFor(p.value)} r={8} className="trend-anomaly-ring" />
                      )}
                    </g>
                  ))}
                  {/* end value label — numbers always accompany the line */}
                  <text
                    className="trend-end-label"
                    x={xFor(pts[pts.length - 1].date) + 8}
                    y={yFor(pts[pts.length - 1].value) - 8}
                  >
                    {mode === "pct" ? `p${Math.round(pts[pts.length - 1].value)}` : formatNumber(pts[pts.length - 1].value, 2)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* legend — names + values, dash pattern per metric */}
        <div className="radar-legend">
          {lines.map((line) => {
            const values = line.points.map((p) => p.value).filter((v): v is number => v !== null);
            const last = values.length ? values[values.length - 1] : null;
            return (
              <span key={line.id} className="radar-legend__item">
                <svg width="22" height="10" aria-hidden="true">
                  <line
                    x1="0"
                    y1="5"
                    x2="22"
                    y2="5"
                    stroke={line.color}
                    strokeWidth="2.5"
                    strokeDasharray={line.dash || undefined}
                  />
                </svg>
                {line.label}
                {last !== null && (
                  <span className="num">· {mode === "pct" ? `p${Math.round(last)}` : formatNumber(last, 2)}</span>
                )}
              </span>
            );
          })}
        </div>

        {events && events.length > 0 && (
          <p className="trend-notes" role="note">
            <strong>Timeline:</strong>{" "}
            {events.map((e, i) => (
              <span key={i}>
                {e.type === "transfer" && (
                  <>
                    Transfer on {e.date.slice(0, 10)}: {e.team_from ?? "unknown"} → {e.team_to ?? "unknown"}
                    {i < events.length - 1 ? " · " : ""}
                  </>
                )}
              </span>
            ))}
          </p>
        )}

        {granularityNote && (
          <p className="trend-notes" role="note">
            {granularityNote}
          </p>
        )}

        {/* data-table alternative (screen readers; numbers never colour-only) */}
        <table className="visually-hidden">
          <caption>Trend data — {aria}</caption>
          <thead>
            <tr>
              <th scope="col">Snapshot date</th>
              {lines.map((line) => (
                <th key={line.id} scope="col">
                  {line.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dates.map((date) => (
              <tr key={date}>
                <th scope="row">{date.slice(0, 10)}</th>
                {lines.map((line) => {
                  const point = line.points.find((p) => p.date === date);
                  return (
                    <td key={line.id}>
                      {point?.value !== null && point?.value !== undefined
                        ? mode === "pct"
                          ? `p${Math.round(point.value)}`
                          : formatNumber(point.value, 2)
                        : "N/A"}
                      {point?.gap_after ? " (gap)" : ""}
                      {point?.anomaly ? " (flagged)" : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
