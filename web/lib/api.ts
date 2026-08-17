import type {
  AssistantQuota,
  ChatResponse,
  CheckoutPayload,
  CoveragePayload,
  EventCoverage,
  EventMatch,
  LeaderboardResponse,
  LeagueStatsRow,
  LeagueSummary,
  LimitsPayload,
  MePayload,
  Meta,
  PassEvent,
  PlayerPayload,
  PortalPayload,
  PositionGroupMeta,
  ReportQuotaPayload,
  ReportsPayload,
  ReportSummary,
  SearchResult,
  ShotEvent,
  ShortlistDetail,
  ShortlistMemberships,
  SimilarPlayer,
  SubscriptionStatusPayload,
  SavedSearchesPayload,
  SearchHistoryPayload,
  SearchPreset,
  SearchResults,
  TagSuggestions,
  TeamPayload,
  TrendPayload,
  WatchAlertsPayload,
  WatchAlertDetail,
  WatchPreferences,
  WatchesPayload,
  WorkspaceOverview,
} from "./types";

// Server components read the API at STATLAS_API_URL (no CORS involved);
// client components read NEXT_PUBLIC_STATLAS_API_URL (CORS configured on the
// API for localhost). Both default to the local FastAPI dev server.
const API_URL =
  typeof window === "undefined"
    ? (process.env.STATLAS_API_URL ?? "http://127.0.0.1:8000")
    : (process.env.NEXT_PUBLIC_STATLAS_API_URL ?? "http://127.0.0.1:8000");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    // The API and web app are different origins (8000 vs 3000), so the
    // session cookie is only sent on credentialed requests — without this,
    // every signed-in GET (me, subscription, workspace…) silently 401s.
    credentials: "include",
    cache: "no-store",
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const q = search.toString();
  return q ? `?${q}` : "";
}

export const api = {
  meta: () => get<Meta>("/api/v1/meta"),
  leagues: () => get<LeagueSummary[]>("/api/v1/leagues"),
  positions: () => get<PositionGroupMeta[]>("/api/v1/positions"),
  coverage: () => get<CoveragePayload>("/api/v1/coverage"),
  playerBySlug: (slug: string) => get<PlayerPayload>(`/api/v1/players/by-slug/${encodeURIComponent(slug)}`),
  playerSearch: (q: string, limit = 8) =>
    get<SearchResult[]>(`/api/v1/players/search${qs({ q, limit })}`),
  similarPlayers: (playerId: number, limit = 5) =>
    get<SimilarPlayer[]>(`/api/v1/players/${playerId}/similar${qs({ limit })}`),
  team: (leagueSlug: string, teamSlug: string) =>
    get<TeamPayload>(`/api/v1/clubs/${encodeURIComponent(leagueSlug)}/${encodeURIComponent(teamSlug)}`),
  leaderboard: (params: {
    metric?: string;
    season?: string;
    league?: string;
    tier?: string;
    position?: string;
    min_minutes?: number;
    page?: number;
    limit?: number;
    sort_by?: string;
    sort_dir?: string;
  }) => get<LeaderboardResponse>(`/api/v1/leaderboard${qs(params)}`),
  leagueStats: (leagueSlug: string, params: { metric?: string; season?: string; limit?: number }) =>
    get<LeagueStatsRow[]>(
      `/api/v1/leagues/${encodeURIComponent(leagueSlug)}/stats${qs(params)}`
    ),
  // Phase 3 — trends (Part A)
  playerTrend: (
    playerId: number,
    params: { metric: string; window?: number },
    init?: RequestInit
  ) => get<TrendPayload>(`/api/v1/players/${playerId}/trend${qs(params)}`, init),
  // Phase 3 — shot / pass maps (Part B, coverage-gated)
  playerEventCoverage: (playerId: number) =>
    get<EventCoverage>(`/api/v1/players/${playerId}/events`),
  playerEventMatches: (
    playerId: number,
    params: { competition?: string; season?: string } = {},
    init?: RequestInit
  ) => get<EventMatch[]>(`/api/v1/players/${playerId}/events/matches${qs(params)}`, init),
  playerShots: (
    playerId: number,
    params: { match?: string; competition?: string; season?: string } = {},
    init?: RequestInit
  ) => get<ShotEvent[]>(`/api/v1/players/${playerId}/events/shots${qs(params)}`, init),
  playerPasses: (
    playerId: number,
    params: { match?: string; competition?: string; season?: string } = {},
    init?: RequestInit
  ) => get<PassEvent[]>(`/api/v1/players/${playerId}/events/passes${qs(params)}`, init),
  // Phase 4 — accounts + billing (Part A). POST helpers use `post` which
  // sends cookies (credentials: "include") so the session cookie is attached.
  register: (email: string, password: string) => post<MePayload>("/api/v1/auth/register", { email, password }),
  login: (email: string, password: string) => post<MePayload>("/api/v1/auth/login", { email, password }),
  logout: () => post<{ ok: boolean }>("/api/v1/auth/logout", {}),
  me: () => get<MePayload>("/api/v1/auth/me"),
  checkout: (successUrl: string, cancelUrl: string) =>
    post<CheckoutPayload>("/api/v1/billing/checkout", { success_url: successUrl, cancel_url: cancelUrl }),
  billingPortal: (returnUrl: string) =>
    post<PortalPayload>("/api/v1/billing/portal", { return_url: returnUrl }),
  subscription: () => get<SubscriptionStatusPayload>("/api/v1/billing/subscription"),
  planLimits: () => get<LimitsPayload>("/api/v1/billing/limits"),
  // Phase 4 — grounded AI assistant (Part B)
  assistantChat: (messages: { role: string; content: string }[]) =>
    post<ChatResponse>("/api/v1/assistant/chat", { messages }),
  assistantQuota: () => get<AssistantQuota>("/api/v1/assistant/quota"),
  // Phase 4 — public API docs (Part C2): live OpenAPI spec, not hand-written.
  openapi: () => get<{ paths?: Record<string, unknown>; info?: { version?: string } }>("/openapi.json"),
  // Phase 7 — scouting workspace. All routes are session-authenticated.
  workspace: () => get<WorkspaceOverview>("/api/v1/workspace"),
  createShortlist: (name: string, description?: string | null) =>
    post<{ shortlist_id: number; name: string }>("/api/v1/workspace", {
      name,
      description: description ?? null,
    }),
  shortlistDetail: (shortlistId: number) =>
    get<ShortlistDetail>(`/api/v1/workspace/${shortlistId}`),
  shortlistMemberships: (playerId: number) =>
    get<ShortlistMemberships>(`/api/v1/workspace/memberships?player_id=${playerId}`),
  tagSuggestions: (prefix: string) =>
    get<TagSuggestions>(`/api/v1/workspace/tag-suggestions?prefix=${encodeURIComponent(prefix)}`),
  addToShortlist: (shortlistId: number, playerId: number, initialNote?: string | null) =>
    post<{ entry_id: number; status: string }>(`/api/v1/workspace/${shortlistId}/entries`, {
      player_id: playerId,
      initial_note: initialNote ?? null,
    }),
  changeEntryStatus: (entryId: number, status: string, reasonNote?: string | null) =>
    post<{ entry_id: number; status: string; history_written: boolean }>(
      `/api/v1/workspace/entries/${entryId}/status`,
      { status, reason_note: reasonNote ?? null }
    ),
  setEntryPriority: (entryId: number, priority: string | null) =>
    post<{ entry_id: number; priority: string | null }>(
      `/api/v1/workspace/entries/${entryId}/priority`,
      { priority }
    ),
  addEntryNote: (entryId: number, noteText: string) =>
    post<{ note_id: number; created_at: string }>(
      `/api/v1/workspace/entries/${entryId}/notes`,
      { note_text: noteText }
    ),
  addEntryTag: (entryId: number, tagText: string) =>
    post<{ tag: string }>(`/api/v1/workspace/entries/${entryId}/tags`, { tag_text: tagText }),
  removeEntryTag: (entryId: number, tagText: string) =>
    post<{ ok: boolean }>(`/api/v1/workspace/entries/${entryId}/tags/remove`, { tag_text: tagText }),
  removeEntry: (entryId: number) => post<{ ok: boolean }>(`/api/v1/workspace/entries/${entryId}/remove`, {}),
  removeShortlist: (shortlistId: number) =>
    post<{ ok: boolean }>(`/api/v1/workspace/${shortlistId}/remove`, {}),
  // Phase 8 — structured search. Execution is public; saved/history are
  // session-authenticated (Phase 7 ownership pattern). Presets are public.
  executeSearch: (
    queryDefinition: unknown,
    params: {
      limit?: number;
      offset?: number;
      sort_by?: string;
      sort_dir?: string;
      log_history?: boolean;
    } = {},
    init?: RequestInit
  ) =>
    post<SearchResults>(
      `/api/v1/search/execute${qs(params as Record<string, string | number | undefined>)}`,
      { query_definition: queryDefinition },
      init
    ),
  searchPresets: () => get<{ presets: SearchPreset[] }>("/api/v1/search/presets"),
  savedSearches: () => get<SavedSearchesPayload>("/api/v1/search/saved"),
  saveSearch: (name: string, queryDefinition: unknown, description?: string | null) =>
    post<SavedSearchesPayload["searches"][number]>("/api/v1/search/saved", {
      name,
      description: description ?? null,
      query_definition: queryDefinition,
    }),
  runSavedSearch: (searchId: number, params: { limit?: number; offset?: number; sort_by?: string; sort_dir?: string } = {}) =>
    post<{ saved: SavedSearchesPayload["searches"][number]; results: SearchResults }>(
      `/api/v1/search/saved/${searchId}/run${qs(params as Record<string, string | number | undefined>)}`,
      {}
    ),
  deleteSavedSearch: (searchId: number) =>
    del<{ ok: boolean }>(`/api/v1/search/saved/${searchId}`),
  searchHistory: (limit = 20) =>
    get<SearchHistoryPayload>(`/api/v1/search/history${qs({ limit })}`),
  rerunHistoryEntry: (historyId: number, params: { limit?: number; offset?: number; sort_by?: string; sort_dir?: string } = {}) =>
    post<{ reran: { history_id: number }; results: SearchResults }>(
      `/api/v1/search/history/${historyId}/rerun${qs(params as Record<string, string | number | undefined>)}`,
      {}
    ),
  // Phase 9 — AI scouting reports. All session-authenticated; generation is
  // Pro-gated with a separate monthly allowance (D5).
  reportQuota: () => get<ReportQuotaPayload>("/api/v1/reports/quota"),
  reports: () => get<ReportsPayload>("/api/v1/reports"),
  generateReport: (playerId: number, shortlistEntryId?: number | null) =>
    post<ReportSummary>("/api/v1/reports", {
      player_id: playerId,
      shortlist_entry_id: shortlistEntryId ?? null,
    }),
  reportDetail: (reportId: number) => get<ReportSummary>(`/api/v1/reports/${reportId}`),
  regenerateReport: (reportId: number) =>
    post<ReportSummary>(`/api/v1/reports/${reportId}/regenerate`, {}),
  deleteReport: (reportId: number) => del<{ ok: boolean }>(`/api/v1/reports/${reportId}`),
  // Exports derive from the single verified report object (C1).
  reportExportUrl: (reportId: number, format: "json" | "pdf" | "csv") =>
    `${API_URL}/api/v1/reports/${reportId}/export.${format}`,
  // Phase 10 — watchlist & alerts. All session-authenticated except the
  // sessionless one-click unsubscribe link (clicked from email).
  watches: () => get<WatchesPayload>("/api/v1/watch"),
  follow: (entityType: "player" | "team", entityId: number, followedMetrics?: string[] | null) =>
    post<{ watch_id: number; entity_type: string; entity_id: number; entity_name: string }>(
      "/api/v1/watch",
      { entity_type: entityType, entity_id: entityId, followed_metrics: followedMetrics ?? null }
    ),
  unfollow: (watchId: number) => post<{ ok: boolean }>(`/api/v1/watch/${watchId}/unfollow`, {}),
  watchAlerts: (params: { include_read?: boolean; include_dismissed?: boolean; limit?: number } = {}) =>
    get<WatchAlertsPayload>(
      `/api/v1/watch/alerts${qs({
        include_read: params.include_read ? "true" : undefined,
        include_dismissed: params.include_dismissed ? "true" : undefined,
        limit: params.limit,
      })}`
    ),
  watchAlert: (alertId: number) => get<WatchAlertDetail>(`/api/v1/watch/alerts/${alertId}`),
  markAlertRead: (alertId: number) => post<{ ok: boolean }>(`/api/v1/watch/alerts/${alertId}/read`, {}),
  dismissAlert: (alertId: number) => post<{ ok: boolean }>(`/api/v1/watch/alerts/${alertId}/dismiss`, {}),
  watchPreferences: () => get<WatchPreferences>("/api/v1/watch/preferences"),
  updateWatchPreferences: (patch: {
    email_enabled?: boolean;
    alert_type_preferences?: Record<string, boolean>;
    digest_frequency?: string;
  }) => post<WatchPreferences>("/api/v1/watch/preferences", patch),
};

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      const parsed = await res.json();
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      /* non-JSON */
    }
    throw new ApiError(res.status, detail);
  }
  // 204 No Content (report delete) has no body — resolve to an empty object.
  if (res.status === 204) return {} as T;
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...(init?.headers ?? {}) },
    body: JSON.stringify(body),
    ...init,
  });
  if (!res.ok) {
    let detail = `API ${res.status}`;
    try {
      const parsed = await res.json();
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      /* non-JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}
