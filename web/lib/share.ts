/**
 * Share / permalink logic (Phase 3 — Part C).
 *
 * Pure functions with ZERO imports so the same module runs in the browser,
 * in server components, and under `node --test` (type-stripping) for the
 * quality-gate tests: a permalink encoded here must decode back to the exact
 * chart configuration — opening a shared link reproduces the chart state with
 * no prior client state.
 *
 * URL scheme (extends the locked routes in design-system.md §2 / site-map.md):
 *   Radar:  /compare?{query}            (mode + players, the shareable form)
 *   Trend:  /trend?{query}
 *   OG:     /compare/og-image?{query}   /trend/og-image?{query}
 *   Embed:  /embed/radar?{query}        /embed/trend?{query}
 *
 * `v=1` is the config version — future phases bump it and decode handles both.
 */

export type RadarMode = "pct" | "raw";

export type RadarShareConfig = {
  kind: "radar";
  players: string[];
  mode: RadarMode;
};

export type TrendShareConfig = {
  kind: "trend";
  players: string[];
  metrics: string[];
  window: number;
  mode: RadarMode;
};

export type ShareConfig = RadarShareConfig | TrendShareConfig;

export const MAX_RADAR_PLAYERS = 4;
export const MAX_TREND_PLAYERS = 3;
export const TREND_WINDOWS = [5, 10] as const;
export const CONFIG_VERSION = "1";

const VALID_MODES: RadarMode[] = ["pct", "raw"];

function splitList(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

function clampWindow(value: number | null): number {
  return value !== null && (TREND_WINDOWS as readonly number[]).includes(value)
    ? value
    : TREND_WINDOWS[0];
}

export function encodeRadarQuery(config: { players: string[]; mode: RadarMode }): string {
  const params = new URLSearchParams();
  params.set("v", CONFIG_VERSION);
  const players = unique(config.players).slice(0, MAX_RADAR_PLAYERS);
  if (players.length) params.set("players", players.join(","));
  if (VALID_MODES.includes(config.mode)) params.set("mode", config.mode);
  return params.toString();
}

export function decodeRadarQuery(search: string): RadarShareConfig {
  const params = new URLSearchParams(search);
  const modeRaw = params.get("mode");
  const mode: RadarMode = VALID_MODES.includes(modeRaw as RadarMode) ? (modeRaw as RadarMode) : "pct";
  return {
    kind: "radar",
    players: unique(splitList(params.get("players"))).slice(0, MAX_RADAR_PLAYERS),
    mode,
  };
}

export function encodeTrendQuery(config: {
  players: string[];
  metrics: string[];
  window: number;
  mode: RadarMode;
}): string {
  const params = new URLSearchParams();
  params.set("v", CONFIG_VERSION);
  const players = unique(config.players).slice(0, MAX_TREND_PLAYERS);
  const metrics = unique(config.metrics);
  if (players.length) params.set("players", players.join(","));
  if (metrics.length) params.set("metrics", metrics.join(","));
  if ((TREND_WINDOWS as readonly number[]).includes(config.window)) {
    params.set("window", String(config.window));
  }
  if (VALID_MODES.includes(config.mode)) params.set("mode", config.mode);
  return params.toString();
}

export function decodeTrendQuery(search: string): TrendShareConfig {
  const params = new URLSearchParams(search);
  const modeRaw = params.get("mode");
  const mode: RadarMode = VALID_MODES.includes(modeRaw as RadarMode) ? (modeRaw as RadarMode) : "pct";
  return {
    kind: "trend",
    players: unique(splitList(params.get("players"))).slice(0, MAX_TREND_PLAYERS),
    metrics: unique(splitList(params.get("metrics"))),
    window: clampWindow(params.get("window") ? Number(params.get("window")) : null),
    mode,
  };
}

export function decodeShareConfig(search: string, kind: "radar" | "trend"): ShareConfig {
  return kind === "radar" ? decodeRadarQuery(search) : decodeTrendQuery(search);
}

/** The canonical shareable page URL for a config. */
export function sharePageUrl(kind: "radar" | "trend", query: string): string {
  return kind === "radar" ? `/compare?${query}` : `/trend?${query}`;
}

/** The OG image URL a crawler fetches when the shared link is previewed. */
export function ogImageUrl(kind: "radar" | "trend", query: string): string {
  return kind === "radar" ? `/compare/og-image?${query}` : `/trend/og-image?${query}`;
}

/** The embed page URL an <iframe> points at. */
export function embedPageUrl(kind: "radar" | "trend", query: string): string {
  return kind === "radar" ? `/embed/radar?${query}` : `/embed/trend?${query}`;
}

export type EmbedCodeOptions = {
  width?: string | number;
  height?: string | number;
  title?: string;
  /**
   * Site origin, e.g. "https://statlas.com". REQUIRED for a working
   * third-party embed: without it the iframe src and attribution href are
   * relative and resolve against the EMBEDDING page's origin instead of
   * Statlas. The SharePanel always passes window.location.origin.
   */
  origin?: string;
};

/**
 * The copy-paste embed snippet (Part C3). Responsive width, lazy-loaded,
 * titled (iframe accessibility), and attributed — the "Powered by Statlas"
 * attribution is rendered INSIDE the widget itself (it cannot be stripped).
 *
 * The src is built from `origin` when provided so the snippet works verbatim
 * on any third-party page (relative URLs would break — see EmbedCodeOptions).
 */
export function buildEmbedCode(kind: "radar" | "trend", query: string, opts: EmbedCodeOptions = {}): string {
  const width = opts.width ?? "100%";
  const height = opts.height ?? (kind === "radar" ? 560 : 480);
  const title =
    opts.title ??
    (kind === "radar"
      ? "Statlas — player comparison radar"
      : "Statlas — snapshot trend chart");
  const src = opts.origin
    ? `${opts.origin}${embedPageUrl(kind, query)}`
    : embedPageUrl(kind, query);
  const attributionHref = opts.origin ? `${opts.origin}/compare` : "/compare";
  return [
    `<iframe src="${src}" title="${title}" width="${width}" height="${height}" loading="lazy" style="border:0;border-radius:12px;overflow:hidden" referrerPolicy="no-referrer-when-downgrade"></iframe>`,
    `<p style="margin:4px 0 0;font:12px/1.4 sans-serif;color:#6B6558">Built with <a href="${attributionHref}" style="color:#144E33;font-weight:600;text-decoration:underline">Statlas</a> — analytics that shows its work</p>`,
  ].join("\n");
}

export type SocialShare = { x: string; linkedin: string };

/** Social share intents (no API keys — plain web intents). */
export function socialShareUrls(absoluteUrl: string, title: string): SocialShare {
  return {
    x: `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(absoluteUrl)}`,
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(absoluteUrl)}`,
  };
}

/** Default metrics for the trend tool when the URL carries none (registry order
 * mirrors the API; these two are the classic progressive-pass comparison). */
export const DEFAULT_TREND_METRICS = ["si_prgp_p90", "si_prgc_p90"] as const;
