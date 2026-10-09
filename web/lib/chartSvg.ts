/**
 * Pure SVG chart builders for Open Graph images (Phase 3 — Part C2).
 *
 * A shared Radar/Trend permalink's og:image must render the ACTUAL chart with
 * the ACTUAL data baked in — not the site-wide banner. next/og (satori)
 * cannot run React components, so these pure functions serialize the same
 * chart language (tokens, gridlines, gap dashes, transfer markers) to SVG
 * markup; the og-image route handlers embed that SVG in an <img>.
 *
 * ZERO imports: the same module runs in route handlers and under `node --test`
 * (type-stripping) so the quality gate — "the generated image contains the
 * real values from the shared configuration" — is automated. Node-first, with
 * a browser-safe base64 fallback (Buffer → TextEncoder + btoa) so the builders
 * stay portable if a future client-side preview reuses them.
 *
 * Colors are the DARK-theme token values from styles/tokens.css, documented
 * inline so the two stay in sync (OG images always render the dark card).
 */

export type OgRadarPlayer = {
  name: string;
  color: string;
  axes: { name: string; value: number | null }[]; // pct (0-100) or raw per-90
};

export type OgTrendSeries = {
  label: string;
  color: string;
  dash: string; // solid | dash | dot
  points: { date: string; value: number | null; gap_after?: boolean }[];
};

// Dark-theme token values (tokens.css) — keep in sync with the CSS.
const C = {
  bg: "#12100D",
  surface: "#1C1A15",
  text: "#F1EFE9",
  muted: "#A8A296",
  faint: "#8A8578",
  gridline: "#2B2822",
  zero: "#413D34",
  green: "#6BC794",
  amber: "#E8B45C",
  accent: "#5CAD82",
  danger: "#E57368",
};

export const OG_PLAYER_COLORS = ["#0072B2", "#D55E00", "#009E73", "#56B4E9"];
export const OG_METRIC_DASHES = ["", "8 6", "2 6"] as const; // solid | dash | dot

function toBase64(svg: string): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(svg, "utf8").toString("base64");
  }
  // Browser fallback — btoa is latin-1 only, so go through TextEncoder first.
  const bytes = new TextEncoder().encode(svg);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

export function svgDataUrl(svg: string): string {
  // Base64, not percent-encoding: satori's <img> data-URL handling does not
  // percent-decode, so a percent-encoded SVG would be parsed as raw XML and
  // fail with InvalidCharacterError on the first "%xx" escape.
  return `data:image/svg+xml;base64,${toBase64(svg)}`;
}

function esc(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function fmt(value: number): string {
  return value.toFixed(1);
}

// ---------------------------------------------------------------------------
// Radar
// ---------------------------------------------------------------------------

export function radarChartSvg(
  players: OgRadarPlayer[],
  opts: { mode: "pct" | "raw"; title: string; subtitle?: string }
): string {
  const W = 1000;
  const H = 760;
  const CX = W / 2;
  const CY = H / 2 - 40;
  const R = 300;
  const LABEL_R = R + 36;
  const n = Math.max(3, players[0]?.axes.length ?? 0);
  const rings = [25, 50, 75, 100];

  const angle = (i: number) => ((-90 + (i * 360) / n) * Math.PI) / 180;
  const polar = (r: number, i: number) => ({
    x: CX + r * Math.cos(angle(i)),
    y: CY + r * Math.sin(angle(i)),
  });
  const ringPoints = (r: number) =>
    Array.from({ length: n }, (_, i) => polar(r, i))
      .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(" ");

  // Per-axis max for raw scaling.
  const rawMax: Record<number, number> = {};
  players.forEach((p) =>
    p.axes.forEach((a, i) => {
      if (a.value !== null) rawMax[i] = Math.max(rawMax[i] ?? 0, a.value);
    })
  );

  const parts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="Sora, sans-serif">`,
    `<rect width="${W}" height="${H}" fill="${C.bg}"/>`,
  ];

  rings.forEach((pct) => {
    parts.push(
      `<polygon points="${ringPoints((R * pct) / 100)}" fill="none" stroke="${C.gridline}" stroke-width="2"/>`
    );
  });
  for (let i = 0; i < n; i += 1) {
    const p = polar(R, i);
    parts.push(`<line x1="${CX}" y1="${CY}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}" stroke="${C.gridline}" stroke-width="2"/>`);
  }

  // Axis labels
  players[0]?.axes.forEach((axis, i) => {
    const p = polar(LABEL_R, i);
    const cos = Math.cos(angle(i));
    const anchor = cos > 0.35 ? "start" : cos < -0.35 ? "end" : "middle";
    const max = rawMax[i];
    const label =
      opts.mode === "pct" ? axis.name : `${axis.name} · ${max !== undefined ? fmt(max) : "—"}`;
    parts.push(
      `<text x="${p.x.toFixed(1)}" y="${p.y.toFixed(1)}" fill="${C.muted}" font-size="22" text-anchor="${anchor}" dominant-baseline="middle">${esc(label)}</text>`
    );
  });

  // Per-player polygons + vertices
  players.forEach((player) => {
    const points: string[] = [];
    player.axes.forEach((axis, i) => {
      if (axis.value === null) return;
      const max = opts.mode === "pct" ? 100 : rawMax[i] ?? 1;
      const frac = Math.max(0, Math.min(1, axis.value / max));
      const p = polar(R * frac, i);
      points.push(`${p.x.toFixed(1)},${p.y.toFixed(1)}`);
    });
    if (points.length < 3) return;
    parts.push(
      `<polygon points="${points.join(" ")}" fill="${player.color}" fill-opacity="0.18" stroke="${player.color}" stroke-width="4"/>`
    );
    player.axes.forEach((axis, i) => {
      if (axis.value === null) return;
      const max = opts.mode === "pct" ? 100 : rawMax[i] ?? 1;
      const frac = Math.max(0, Math.min(1, axis.value / max));
      const p = polar(R * frac, i);
      parts.push(
        `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="7" fill="${player.color}" stroke="${C.surface}" stroke-width="2"/>`
      );
    });
  });

  // Legend: player name + top-three metric values — the numbers are always
  // rendered, never colour alone (Constitution §2).
  const legendY = CY + R + 110;
  players.forEach((player, index) => {
    const cols = 2;
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = CX - 240 + col * 280;
    const y = legendY + row * 86;
    const top = [...player.axes]
      .filter((a) => a.value !== null)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
      .slice(0, 3);
    const sub =
      top.length > 0
        ? top.map((a) => `${a.name} · ${opts.mode === "pct" ? Math.round(a.value as number) : fmt(a.value as number)}`).join(" · ")
        : "no values yet";
    parts.push(
      `<rect x="${x}" y="${y - 20}" width="26" height="26" rx="6" fill="${player.color}"/>` +
        `<text x="${x + 38}" y="${y}" fill="${C.text}" font-size="26" font-weight="600">${esc(player.name)}</text>` +
        `<text x="${x + 38}" y="${y + 30}" fill="${C.muted}" font-size="19">${esc(sub)}</text>`
    );
  });

  // Title + subtitle
  parts.push(`<text x="${CX}" y="56" fill="${C.text}" font-size="34" font-weight="700" text-anchor="middle">${esc(opts.title)}</text>`);
  if (opts.subtitle) {
    parts.push(`<text x="${CX}" y="92" fill="${C.muted}" font-size="22" text-anchor="middle">${esc(opts.subtitle)}</text>`);
  }
  parts.push(`</svg>`);
  return parts.join("");
}

// ---------------------------------------------------------------------------
// Trend
// ---------------------------------------------------------------------------

export function trendChartSvg(
  series: OgTrendSeries[],
  opts: { mode: "pct" | "raw"; unit: string; title: string; granularityNote: string }
): string {
  const W = 1000;
  const H = 620;
  const PAD_L = 70;
  const PAD_R = 30;
  const PAD_T = 110;
  const PAD_B = 90;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const allValues = series.flatMap((s) =>
    s.points.map((p) => p.value).filter((v): v is number => v !== null)
  );
  const isPct = opts.mode === "pct";
  const yMax = isPct ? 100 : Math.max(0, ...allValues) * 1.15 || 1;
  const yMin = isPct ? 0 : 0; // value axes start at zero (design-system §7)

  // Union of all point dates for the x positions.
  const allDates = Array.from(
    new Set(series.flatMap((s) => s.points.map((p) => p.date)))
  ).sort();
  const xFor = (date: string) =>
    PAD_L + (allDates.length <= 1 ? plotW / 2 : (allDates.indexOf(date) / (allDates.length - 1)) * plotW);
  const yFor = (value: number) =>
    PAD_T + plotH - ((value - yMin) / (yMax - yMin)) * plotH;

  const parts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" font-family="Sora, sans-serif">`,
    `<rect width="${W}" height="${H}" fill="${C.bg}"/>`,
  ];

  // Gridlines + y labels
  const steps = 4;
  for (let i = 0; i <= steps; i += 1) {
    const value = yMin + (i / steps) * (yMax - yMin);
    const y = yFor(value);
    parts.push(
      `<line x1="${PAD_L}" y1="${y.toFixed(1)}" x2="${W - PAD_R}" y2="${y.toFixed(1)}" stroke="${i === 0 ? C.zero : C.gridline}" stroke-width="2"/>` +
        `<text x="${PAD_L - 14}" y="${(y + 7).toFixed(1)}" fill="${C.muted}" font-size="20" text-anchor="end">${isPct ? Math.round(value) : fmt(value)}</text>`
    );
  }

  // X labels (first, middle, last dates)
  const labelIndexes = [0, Math.floor((allDates.length - 1) / 2), allDates.length - 1];
  labelIndexes.forEach((i) => {
    if (i < 0 || i >= allDates.length) return;
    const date = allDates[i];
    parts.push(
      `<text x="${xFor(date).toFixed(1)}" y="${H - PAD_B + 34}" fill="${C.muted}" font-size="20" text-anchor="middle">${esc(date.slice(0, 10))}</text>`
    );
  });

  // Series
  series.forEach((s) => {
    const pts = s.points.filter((p) => p.value !== null) as { date: string; value: number; gap_after?: boolean }[];
    if (!pts.length) return;

    // Solid path segments, dashed across gaps — never a false interpolation.
    let current: string[] = [];
    const segs: { d: string; dashed: boolean }[] = [];
    pts.forEach((p, i) => {
      current.push(`${xFor(p.date).toFixed(1)},${yFor(p.value).toFixed(1)}`);
      if (p.gap_after && i + 1 < pts.length) {
        segs.push({ d: `M${current.join(" L")} L${xFor(pts[i + 1].date).toFixed(1)},${yFor(pts[i + 1].value).toFixed(1)}`, dashed: true });
        current = [];
      }
    });
    if (current.length) segs.push({ d: `M${current.join(" L")}`, dashed: false });

    const dashAttr = s.dash ? `stroke-dasharray="${s.dash}"` : "";
    segs.forEach((seg) => {
      parts.push(
        `<path d="${seg.d}" fill="none" stroke="${s.color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" ${seg.dashed ? 'stroke-dasharray="4 10"' : dashAttr}/>`
      );
    });
    pts.forEach((p) => {
      parts.push(
        `<circle cx="${xFor(p.date).toFixed(1)}" cy="${yFor(p.value).toFixed(1)}" r="6" fill="${s.color}" stroke="${C.bg}" stroke-width="2"/>`
      );
    });
    // End value label — the shared preview shows the real numbers, and the
    // value is never conveyed by colour alone.
    const last = pts[pts.length - 1];
    const lx = xFor(last.date) + 14;
    const ly = yFor(last.value) - 12;
    parts.push(
      `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" fill="${C.text}" font-size="22" font-weight="600">${isPct ? Math.round(last.value) : fmt(last.value)}</text>`
    );
  });

  // Legend (label + color + dash pattern)
  series.forEach((s, i) => {
    const x = PAD_L + i * 300;
    const y = H - 26;
    parts.push(
      `<line x1="${x}" y1="${y}" x2="${x + 40}" y2="${y}" stroke="${s.color}" stroke-width="5" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""}/>` +
        `<text x="${x + 52}" y="${y + 7}" fill="${C.text}" font-size="22">${esc(s.label)}</text>`
    );
  });

  parts.push(`<text x="${PAD_L}" y="52" fill="${C.text}" font-size="34" font-weight="700">${esc(opts.title)}</text>`);
  parts.push(`<text x="${PAD_L}" y="84" fill="${C.muted}" font-size="20">${esc(opts.granularityNote)}</text>`);
  parts.push(`</svg>`);
  return parts.join("");
}

/** Brand footer rendered under every OG chart (subtle wordmark, Part C2). */
export function ogFooter(title: string, recency: string | null): string {
  const parts = [esc(title)];
  if (recency) parts.push(` · ${esc(recency)}`);
  parts.push(" · Statlas — analytics that shows its work");
  return parts.join("");
}
