// Formatting helpers for Phase 10 watch alerts. Every string is populated
// from the alert's real `detail` values (never generic copy) — the same
// checkable-data discipline as every other surface in the product.

import type { AlertType } from "./types";
import type { WatchAlertItem } from "./types";

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  percentile_movement: "Percentile movement",
  club_change: "Club change",
  new_season_data: "New season data",
  data_coverage_change: "Data coverage change",
};

export const ALERT_TYPE_ICONS: Record<AlertType, string> = {
  percentile_movement: "📈",
  club_change: "🔁",
  new_season_data: "🗓️",
  data_coverage_change: "📊",
};

function ordinal(n: number): string {
  const rounded = Math.round(n);
  if (10 <= rounded % 100 && rounded % 100 <= 20) return `${rounded}th`;
  const suffix = { 1: "st", 2: "nd", 3: "rd" }[rounded % 10] ?? "th";
  return `${rounded}${suffix}`;
}

function pct(value: unknown): string {
  return typeof value === "number" ? ordinal(value) : "—";
}

/**
 * One-line, real-data summary of an alert for list views (bell, watchlist).
 * e.g. "Progressive passes per 90: 62nd → 81st percentile (Aug 12)"
 */
export function formatAlertDetail(alert: WatchAlertItem): string {
  const d = alert.detail;
  switch (alert.alert_type) {
    case "percentile_movement":
      return `${String(d.metric_name ?? d.metric ?? "")}: ${pct(d.from_percentile)} → ${pct(
        d.to_percentile
      )} percentile`;
    case "club_change":
      return `${String(d.from_team ?? "—")} → ${String(d.to_team ?? "—")}`;
    case "new_season_data":
      return `${String(d.new_season ?? "")} season data available`;
    case "data_coverage_change":
      return d.signal === "coverage_gained"
        ? `Detailed ${String(d.coverage_source ?? "")} data now available`
        : `Data-quality flag (${String(d.anomaly_count ?? "?")} unresolved)`;
    default:
      return "";
  }
}

/** Long-form detail for the alert detail view — full real supporting values. */
export function formatAlertLong(alert: WatchAlertItem): { label: string; value: string }[] {
  const d = alert.detail;
  switch (alert.alert_type) {
    case "percentile_movement":
      return [
        { label: "Metric", value: String(d.metric_name ?? d.metric ?? "") },
        { label: "Previous percentile", value: pct(d.from_percentile) },
        { label: "Current percentile", value: pct(d.to_percentile) },
        { label: "Previous snapshot", value: String(d.from_snapshot_date ?? "—") },
        { label: "Current snapshot", value: String(d.to_snapshot_date ?? "—") },
        { label: "Minutes", value: `${String(d.from_minutes ?? "—")} → ${String(d.to_minutes ?? "—")}` },
      ];
    case "club_change":
      return [
        { label: "From club", value: String(d.from_team ?? "—") },
        { label: "To club", value: String(d.to_team ?? "—") },
        { label: "Snapshot date", value: String(d.snapshot_date ?? "—") },
      ];
    case "new_season_data":
      return [
        { label: "New season", value: String(d.new_season ?? "—") },
        { label: "Previous season", value: String(d.previous_season ?? "—") },
        { label: "Snapshot date", value: String(d.snapshot_date ?? "—") },
      ];
    case "data_coverage_change":
      return d.signal === "coverage_gained"
        ? [
            { label: "Signal", value: "Event-data coverage gained" },
            { label: "Source", value: String(d.coverage_source ?? "—") },
            { label: "League", value: String(d.league ?? "—") },
            { label: "Season", value: String(d.season ?? "—") },
          ]
        : [
            { label: "Signal", value: "Source data-quality flag" },
            { label: "Unresolved issues", value: String(d.anomaly_count ?? "—") },
            { label: "Snapshot date", value: String(d.snapshot_date ?? "—") },
          ];
    default:
      return [];
  }
}

/** Entity profile href from an alert's watch metadata. */
export function entityHref(alert: WatchAlertItem): string {
  const slug = alert.slug;
  if (!slug) return "/watchlist";
  if (alert.entity_type === "player") return `/players/${slug}`;
  // Team profiles are league-scoped (clubs/[leagueSlug]/[teamSlug]).
  return alert.league_slug ? `/clubs/${alert.league_slug}/${slug}` : "/watchlist";
}

export type { WatchAlertItem };
