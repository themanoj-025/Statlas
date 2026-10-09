/**
 * Shared chart tokens (design-system.md §7): the Okabe-Ito categorical set is
 * the ONLY comparison palette on the site; metric lines are distinguished by
 * dash pattern on top of the player colour (colour is never the only signal).
 */
export const PLAYER_COLORS = [
  "var(--cat-blue)",
  "var(--cat-vermillion)",
  "var(--cat-green)",
  "var(--cat-sky)",
] as const;

/** SVG stroke-dasharray per metric index (solid | dash | dot). */
export const METRIC_DASHES = ["", "8 6", "2 6"] as const;

export function playerColor(index: number): string {
  return PLAYER_COLORS[index % PLAYER_COLORS.length];
}

export function metricDash(index: number): string {
  return METRIC_DASHES[index % METRIC_DASHES.length];
}
