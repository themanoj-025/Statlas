export type LeagueSummary = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  team_count: number;
  has_fbref_coverage: boolean;
  seasons_available: string[];
  sources: string[];
};

export type RosterEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  position_label: string | null;
  nationality: string | null;
  minutes: number;
  matches: number;
  index: number | null;
  snapshot_date: string;
  season: string;
};

export type TeamPayload = {
  team_id: number;
  name: string;
  slug: string;
  league_id: number;
  league: string;
  league_slug: string;
  tier: string;
  logo_url: string | null;
  founded_year: number | null;
  roster: RosterEntry[];
  squad_radar: {
    snapshot_date: string | null;
    n_players: number;
    metrics: { id: string; avg_pct: number; n: number }[];
  } | null;
  roster_count: number;
  qualified_count: number;
};

export type LeagueStatsRow = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  minutes: number;
  matches: number;
  value: number | null;
  status: string;
  snapshot_date: string;
  season: string;
};

// ---------------------------------------------------------------------------
// Phase 3 — trends (Part A)
// ---------------------------------------------------------------------------

export type LeagueCategoryEntry = {
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  club: string | null;
  value: number | null;
  minutes: number;
};

export type LeagueHubPayload = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  season: string;
  team_count: number;
  player_count: number;
  has_fbref_coverage: boolean;
  has_understat_coverage: boolean;
  has_statsbomb_coverage: boolean;
  standings_available: boolean;
  latest_snapshot_date: string | null;
  categories: {
    key: string;
    label: string;
    metric: string;
    metric_name: string;
    entries: LeagueCategoryEntry[];
  }[];
  emerging_players: EmergingPlayerEntry[];
  teams: {
    team_id: number;
    name: string;
    slug: string;
    logo_url: string | null;
  }[];
  coverage: { source: string; status: string; seasons_available: string[] }[];
};

export type LeagueIndexEntry = {
  slug: string;
  name: string;
  country: string;
  tier: string;
  tier_label: string;
  team_count: number;
  has_fbref_coverage: boolean;
  seasons_available: string[];
};

// Human-readable labels for alert types + digest frequencies (single source
// in the frontend; backend enum codes stay stable).
export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  percentile_movement: "Percentile movement",
  club_change: "Club change",
  new_season_data: "New season data",
  data_coverage_change: "Data coverage change",
};

export const DIGEST_FREQUENCY_LABELS: Record<DigestFrequency, string> = {
  immediate: "Immediately (per alert)",
  daily_digest: "Daily digest",
  weekly_digest: "Weekly digest",
};

export const EMERGING_SCORE_THRESHOLD = 0.50;

// Phase 13 — dashboard types
