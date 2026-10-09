"use client";

import { useId, useMemo, useRef, useState } from "react";
import type { Axis } from "@/lib/types";
import { formatNumber } from "@/lib/format";

export type RadarPlayer = {
  id: number;
  name: string;
  color: string;
  axes: Axis[];
  index: number | null;
};

export type RadarMode = "pct" | "raw";

type Tooltip = {
  axis: Axis;
  player: RadarPlayer;
  x: number;
  y: number;
} | null;

const RING_PCTS = [25, 50, 75, 100];

function axisAngle(index: number, total: number): number {
  return (-90 + (index * 360) / total) * (Math.PI / 180);
}

function polar(cx: number, cy: number, r: number, angle: number): { x: number; y: number } {
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
}

function anchorFor(angle: number): "start" | "middle" | "end" {
  const cos = Math.cos(angle);
  if (cos > 0.35) return "start";
  if (cos < -0.35) return "end";
  return "middle";
}

function describe(players: RadarPlayer[], mode: RadarMode): string {
  if (!players.length) return "No players selected.";
  if (mode === "pct") {
    const lines = players.map((p) => {
      const valid = p.axes.filter((a) => a.pct !== null);
      if (!valid.length) return `${p.name}: no percentile values available.`;
      const top = valid.reduce((a, b) => (a.pct! >= b.pct! ? a : b));
      const bottom = valid.reduce((a, b) => (a.pct! <= b.pct! ? a : b));
      return `${p.name}: highest ${top.name} at the ${Math.round(top.pct!)}th percentile, lowest ${bottom.name} at the ${Math.round(bottom.pct!)}th.`;
    });
    return `Radar showing percentile ranks across ${players[0].axes.length} metrics. ${lines.join(" ")}`;
  }
  const lines = players.map(
    (p) => `${p.name}: raw per-90 values, each axis scaled to the highest displayed value.`
  );
  return `Radar showing raw per-90 values. ${lines.join(" ")}`;
}

function skeletonPolygon(cx: number, cy: number, r: number, n: number, inset = 0.62): string {
  const points: string[] = [];
  for (let i = 0; i < n; i += 1) {
    const { x, y } = polar(cx, cy, r * inset, axisAngle(i, n));
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return points.join(" ");
}

export function RadarChart({
  players,
  mode,
  title,
  subtitle,
  recency,
  loading = false,
  emptyTitle,
  emptyBody,
  error,
  onRetry,
  insufficientNote,
}: {
  players: RadarPlayer[];
  mode: RadarMode;
  title: string;
  subtitle?: string;
  recency?: string | null;
  loading?: boolean;
  emptyTitle?: string;
  emptyBody?: React.ReactNode;
  error?: string | null;
  onRetry?: () => void;
  insufficientNote?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const [tooltip, setTooltip] = useState<Tooltip>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const n = players[0]?.axes.length ?? 0;
  const SVG_W = 620;
  const SVG_H = 540;
  const CX = SVG_W / 2;
  const CY = SVG_H / 2;
  const R = 200;
  const LABEL_R = R + 22;

  // Per-axis max raw value across displayed players (raw mode scaling).
  const rawMaxByAxis = useMemo(() => {
    const map: Record<string, number> = {};
    for (const player of players) {
      for (const axis of player.axes) {
        if (axis.raw === null) continue;
        map[axis.id] = Math.max(map[axis.id] ?? 0, axis.raw);
      }
    }
    return map;
  }, [players]);

  const ringRadius = (fraction: number) => R * fraction;

  if (loading) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="radar-skeleton" role="status" aria-label={`Loading radar for ${title}`}>
            <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} aria-hidden="true">
              {RING_PCTS.map((pct) => (
                <polygon
                  key={pct}
                  className="radar-ring"
                  points={skeletonPolygon(CX, CY, ringRadius(pct / 100), n)}
                />
              ))}
              {Array.from({ length: n }, (_, i) => {
                const { x, y } = polar(CX, CY, R, axisAngle(i, n));
                return <line key={i} className="radar-spoke" x1={CX} y1={CY} x2={x} y2={y} />;
              })}
              <polygon className="radar-ring" points={skeletonPolygon(CX, CY, R, n, 0.7)} />
            </svg>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="state-block state-block--error" role="alert">
            <p className="state-block__title">We couldn&rsquo;t load radar data.</p>
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

  if (!players.length) {
    return (
      <div className="radar-card">
        <div className="radar-card__header">
          <h2 className="radar-card__title">{title}</h2>
        </div>
        <div className="radar-card__body">
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__title">{emptyTitle ?? "No radar to draw yet"}</p>
            <p className="state-block__body">{emptyBody}</p>
          </div>
        </div>
      </div>
    );
  }

  const firstAxes = players[0].axes;
  const tooltipText = describe(players, mode);

  const showTooltip = (axis: Axis, player: RadarPlayer, index: number) => {
    const { x, y } = polar(CX, CY, R * 0.95, axisAngle(index, n));
    setTooltip({ axis, player, x, y });
  };

  return (
    <div className="radar-card">
      <div className="radar-card__header">
        <div>
          <h2 className="radar-card__title">{title}</h2>
          {subtitle && <p style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>{subtitle}</p>}
        </div>
        {recency && <span className="recency">Data as of {recency}</span>}
      </div>

      <div className="radar-card__body">
        <div className="radar-svg-wrap" ref={wrapRef}>
          <svg
            className="radar-svg"
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            role="img"
            aria-label={tooltipText}
          >
            {/* rings + spokes */}
            {RING_PCTS.map((pct) => (
              <polygon
                key={pct}
                className="radar-ring"
                points={skeletonPolygon(CX, CY, ringRadius(pct / 100), n)}
              />
            ))}
            {Array.from({ length: n }, (_, i) => {
              const { x, y } = polar(CX, CY, R, axisAngle(i, n));
              return <line key={i} className="radar-spoke" x1={CX} y1={CY} x2={x} y2={y} />;
            })}

            {/* axis labels (selectable text) */}
            {firstAxes.map((axis, i) => {
              const angle = axisAngle(i, n);
              const { x, y } = polar(CX, CY, LABEL_R, angle);
              const anchor = anchorFor(angle);
              const maxRaw = rawMaxByAxis[axis.id];
              const display =
                mode === "pct" ? axis.name : `${axis.name}${maxRaw !== undefined ? ` · ${maxRaw}` : ""}`;
              const insufficient = players.some((p) => p.axes[i]?.status !== "qualified");
              return (
                <text
                  key={`${uid}-label-${axis.id}`}
                  className={`axis-label ${insufficient ? "" : "axis-label--strong"}`}
                  x={x}
                  y={y}
                  textAnchor={anchor}
                  dominantBaseline="middle"
                  onMouseEnter={() => showTooltip(axis, players[0], i)}
                  onMouseLeave={() => setTooltip(null)}
                >
                  {display}
                </text>
              );
            })}

            {/* per-player polygons */}
            {players.map((player) => {
              const points: string[] = [];
              player.axes.forEach((axis, i) => {
                const value = mode === "pct" ? axis.pct : axis.raw;
                if (value === null) return;
                const max = mode === "pct" ? 100 : rawMaxByAxis[axis.id] ?? 1;
                const frac = Math.max(0, Math.min(1, value / max));
                const { x, y } = polar(CX, CY, R * frac, axisAngle(i, n));
                points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
              });
              if (points.length < 3) return null;
              return (
                <g key={player.id}>
                  <polygon
                    className="radar-poly"
                    points={points.join(" ")}
                    fill={player.color}
                    stroke={player.color}
                  />
                  {player.axes.map((axis, i) => {
                    const value = mode === "pct" ? axis.pct : axis.raw;
                    if (value === null) return null;
                    const max = mode === "pct" ? 100 : rawMaxByAxis[axis.id] ?? 1;
                    const frac = Math.max(0, Math.min(1, value / max));
                    const { x, y } = polar(CX, CY, R * frac, axisAngle(i, n));
                    return (
                      <circle
                        key={`${player.id}-${axis.id}`}
                        className="radar-vertex"
                        cx={x}
                        cy={y}
                        r={4}
                        fill={player.color}
                        stroke="var(--color-surface-raised)"
                        strokeWidth={1.5}
                        onMouseEnter={() => showTooltip(axis, player, i)}
                        onMouseLeave={() => setTooltip(null)}
                      />
                    );
                  })}
                </g>
              );
            })}
          </svg>

          {tooltip && (
            <div
              className="radar-axis-tooltip"
              role="tooltip"
              style={{
                left: `${(tooltip.x / SVG_W) * 100}%`,
                top: `${(tooltip.y / SVG_H) * 100}%`,
                transform: "translate(-50%, -110%)",
              }}
            >
              <div className="radar-axis-tooltip__name">
                <span style={{ color: tooltip.player.color }}>●</span> {tooltip.axis.name}
              </div>
              <div>
                {mode === "pct"
                  ? `Percentile ${tooltip.axis.pct !== null ? `p${Math.round(tooltip.axis.pct)}` : "N/A"}`
                  : `${formatNumber(tooltip.axis.raw, 2)} ${tooltip.axis.unit}`}
                {" · "}
                {formatNumber(tooltip.axis.raw, 2)} {tooltip.axis.unit}
              </div>
              <div style={{ color: "var(--color-text-muted)", marginTop: 4 }}>{tooltip.axis.definition}</div>
            </div>
          )}
        </div>

        {/* legend — names always visible, never color alone */}
        <div className="radar-legend">
          {players.map((player) => (
            <span key={player.id} className="radar-legend__item">
              <span className="radar-legend__swatch" style={{ background: player.color }} aria-hidden="true" />
              {player.name}
              {player.index !== null && <span className="num">· {player.index.toFixed(1)}</span>}
            </span>
          ))}
        </div>

        {mode === "raw" && (
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "var(--space-2) 0 0" }}>
            Raw per-90 view — each axis is scaled to the highest value displayed on that axis; the
            per-axis maximum is shown next to the axis name.
          </p>
        )}

        {insufficientNote && (
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-warning)", margin: "var(--space-2) 0 0" }}>
            {insufficientNote}
          </p>
        )}

        {/* data-table alternative (visually hidden, screen-reader accessible) */}
        <table className="visually-hidden">
          <caption>Radar data — {tooltipText}</caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              {firstAxes.map((axis) => (
                <th key={axis.id} scope="col">
                  {axis.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {players.map((player) => (
              <tr key={player.id}>
                <th scope="row">{player.name}</th>
                {player.axes.map((axis) => (
                  <td key={axis.id}>{mode === "pct" ? axis.pct ?? "N/A" : axis.raw ?? "N/A"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
