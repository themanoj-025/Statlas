export type Meta = {
  qualifying_minutes: number;
  display_floor_minutes: number;
  min_pool_size: number;
  index_metric_id: string;
  metrics: Record<string, MetricMeta>;
  position_groups: PositionGroupMeta[];
  tiers: { code: string; label: string; league_slugs: string[] }[];
  weekly_refresh: string;
  weekly_refresh_cadence: string;
  dataset: DatasetInfo;
};

export type MetricMeta = {
  id: string;
  name: string;
  unit: string;
  definition: string;
  direction: string;
  lower_is_better: boolean;
  null_vs_zero: string;
  display_floor?: { type: string; value: number } | null;
  kind: string;
};

export type PositionGroupMeta = {
  code: string;
  label: string;
  plural: string;
  metric_ids: string[];
  weights: Record<string, number>;
  qualifying_counts?: Record<string, number>;
};

export type Plan = "free" | "pro" | "api_business";

export type MePayload = {
  user_id: number;
  email: string;
  plan: Plan;
  has_pro: boolean;
  display_name: string | null;
  email_verified_at: string | null;
  account_status: string;
  timezone: string | null;
  locale: string | null;
};

export type SubscriptionStatusPayload = {
  has_pro: boolean;
  plan: Plan;
  status: string | null;
  current_period_end: string | null;
  grace_period_end: string | null;
  billing_configured: boolean;
  portal_enabled: boolean;
};

export type CheckoutPayload = { url: string; session_id: string };
export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
};

export type ShortlistMemberships = { shortlist_ids: number[] };

// ---------------------------------------------------------------------------
// Phase 8 — structured search (saved searches, presets, history)
// ---------------------------------------------------------------------------
// Grammar documented in docs/product/query-builder-scope.md. Backend enforces
// AND-only logic, max 8 conditions, and the always-applied minutes floor.

export type ReportDocument = {
  player_id: number;
  generated_at: string;
  generated_by_user_id: number;
  data_snapshot_date: string;
  source: "player_profile" | "shortlist_entry";
  shortlist_entry_id: number | null;
  sections: ReportSection;
  confidence: ReportConfidence;
  evidence_appendix: ReportEvidenceItem[];
  verification: { status: "passed" | "needs_review"; log: { attempts: number; unverified: unknown[]; passed: boolean } };
};

export type OrgMember = {
  user_id: number;
  email: string;
  display_name: string | null;
  role: string;
  joined_at: string | null;
};

export type Comment = {
  comment_id: number;
  author: string;
  author_user_id: number;
  text: string;
  parent_id: number | null;
  created_at: string | null;
  edited_at: string | null;
};

// ---------------------------------------------------------------------------
// Phase 17 — Tactical Intelligence
// ---------------------------------------------------------------------------

