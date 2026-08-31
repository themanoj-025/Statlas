export type AlertType =
  | "percentile_movement"
  | "club_change"
  | "new_season_data"
  | "data_coverage_change";

export type DigestFrequency = "immediate" | "daily_digest" | "weekly_digest";

export type WatchItem = {
  watch_id: number;
  entity_type: "player" | "team";
  entity_id: number;
  entity_name: string;
  slug: string | null;
  league_slug?: string | null;
  followed_metrics: string[] | null;
  created_at: string;
  unread_alert_count: number;
  team?: string | null;
  position_group?: string | null;
  league?: string | null;
};

export type WatchAlertItem = {
  alert_id: number;
  watch_id: number;
  entity_type: "player" | "team";
  entity_id: number;
  entity_name: string;
  slug: string | null;
  league_slug?: string | null;
  alert_type: AlertType;
  triggered_at: string;
  detail: Record<string, unknown>;
  delivered_at: string | null;
  read_at: string | null;
  dismissed: boolean;
};

export type WatchPreferences = {
  email_enabled: boolean;
  alert_type_preferences: Record<AlertType, boolean>;
  digest_frequency: DigestFrequency;
  updated_at: string;
};

// ---------------------------------------------------------------------------
// Phase 11 — league hub / emerging players
// ---------------------------------------------------------------------------

export type WatchesPayload = { watches: WatchItem[] };
export type WatchAlertsPayload = { alerts: WatchAlertItem[] };
export type WatchAlertDetail = WatchAlertItem;

export type DashboardActivityItem = {
  entity_type: string;
  entity_id: number;
  action_type: string;
  performed_at: string;
  player_name?: string;
  team_name?: string | null;
  position_group?: string;
};

export type AnalyticsAlert = {
  id: number;
  alert_name: string;
  metric_name: string;
  threshold_type: string;
  threshold_value: number;
  actual_value: number;
  message: string;
  fired_at: string | null;
  acknowledged_at: string | null;
};

export type AnomalyResult = {
  metric_name: string;
  anomaly_detected: boolean;
  anomaly: {
    metric_name: string;
    current_avg: number;
    historical_mean: number;
    std_dev: number;
    z_score: number;
    sigma_threshold: number;
    window_weeks: number;
    message: string;
  } | null;
};
