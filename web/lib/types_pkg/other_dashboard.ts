export type EntryStatus =
  | "discovered"
  | "monitoring"
  | "scouted"
  | "shortlisted"
  | "reviewed"
  | "rejected"
  | "signed";

export type EntryPriority = "low" | "medium" | "high" | null;

export type ShortlistSummary = {
  shortlist_id: number;
  name: string;
  description: string | null;
  entry_count: number;
  status_breakdown: Record<EntryStatus, number>;
  created_at: string;
  updated_at: string;
};

export type WorkspaceOverview = {
  plan: Plan;
  has_pro: boolean;
  limits: Record<string, number | null>;
  shortlists: ShortlistSummary[];
};

export type EntryNote = {
  id: number;
  author_user_id: number;
  note_text: string;
  created_at: string;
};

export type StatusHistoryRow = {
  from_status: EntryStatus | null;
  to_status: EntryStatus;
  changed_by_user_id: number;
  changed_at: string;
  reason_note: string | null;
};

export type ShortlistEntryDetail = {
  entry_id: number;
  player_id: number;
  name: string;
  slug: string | null;
  position_group: string | null;
  position_label: string | null;
  club: string | null;
  league: string | null;
  index: number | null;
  snapshot_date: string | null;
  status: EntryStatus;
  priority: EntryPriority;
  added_at: string;
  updated_at: string;
  added_by_note: string | null;
  notes: EntryNote[];
  tags: string[];
  status_history: StatusHistoryRow[];
};

export type ShortlistDetail = WorkspaceOverview & {
  shortlist_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  entries: ShortlistEntryDetail[];
  entry_count: number;
  status_breakdown: Record<EntryStatus, number>;
};

export type TagSuggestions = { tags: string[] };
    shortlist_status: EntryStatus;
    priority: EntryPriority;
    tags: string[];
    recent_notes: { note_text: string; created_at: string }[];
    label: string;
  } | null;
};

export type DashboardWorkspace = {
  shortlist_count: number;
  saved_search_count: number;
  report_count: number;
  watch_count: number;
  unread_alert_count: number;
};

export type DashboardSummary = {
  recent_activity: DashboardActivityItem[];
  workspace: DashboardWorkspace;
  trending_players: DashboardTrendingPlayer[];
  recommended_players: DashboardRecommendedPlayer[];
  saved_players: DashboardSavedPlayer[];
  transfer_opportunities: OpportunityCard[];
};

// ---------------------------------------------------------------------------
// Phase 14 — Player Archetypes (ML clustering)
// ---------------------------------------------------------------------------
// Constitution Addendum §1.2: Archetypes are patterns, not predictions.
// Every archetype output is labeled as a statistical pattern.
