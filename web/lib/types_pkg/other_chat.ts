export type DatasetInfo = {
  mode: string;
  note: string;
};

export type Axis = MetricMeta & {
  raw: number | null;
  pct: number | null;
  status: "qualified" | "below_floor" | "no_data" | "unranked_pool";
};

export type LimitsPayload = {
  plan: Plan;
  limits: Record<string, number | null>;
};

export type PortalPayload = { url: string };

// --- Phase 4: AI assistant (Part B) -----------------------------------------

export type ToolCall = {
  name: string;
  input: Record<string, unknown>;
  result: unknown;
};

export type AssistantQuota = {
  used: number;
  limit: number;
  reset: string;
  remaining: number;
};

export type ChatResponse = {
  reply: string;
  tool_calls: ToolCall[];
  quota: AssistantQuota;
  grounded: boolean;
};

// --- Phase 7: scouting workspace --------------------------------------------

