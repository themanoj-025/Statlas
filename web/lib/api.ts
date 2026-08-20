import type {
  AssistantQuota,
  ChatResponse,
  CheckoutPayload,
  CoveragePayload,
  DashboardSummary,
  EventCoverage,
  EventMatch,
  LeagueHubPayload,
  LeagueIndexEntry,
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
  ArchetypeOverview,
  ArchetypeDetail,
  PlayerArchetype,
  ValuationComparison,
  TransferCandidateResult,
  CandidateTemplate,
  OpportunityCard,
  TransferRisk,
  ValuationConfidence,
  ValuationGapPlayer,
  PositionScarcityOpportunity,
  OrgSummary,
  OrgDetail,
  OrgMember,
  OrgInviteResult,
  OrgJoinResult,
  OrgSettings,
  AuditEntry,
  Comment,
  PassingNetworkResult,
  PressureMap,
  PossessionMap,
  FormationResult,
  TacticalOverview,
  DauResult,
  MauResult,
  FeatureUsageResult,
  ConversionFunnel,
  RetentionCohort,
  ChurnResult,
  ArpuResult,
  ExecutiveDashboard,
  AnalyticsAlert,
  AnomalyResult,
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
  }) => put<WatchPreferences>("/api/v1/watch/preferences", patch),
  // Phase 11 — league hub / emerging players
  leagueHub: (leagueSlug: string, season?: string) =>
    get<LeagueHubPayload>(`/api/v1/leagues/${encodeURIComponent(leagueSlug)}/hub${qs({ season })}`),
  leaguesIndex: () => get<LeagueIndexEntry[]>("/api/v1/leagues"),
  // Phase 12 — account profile, password reset, email verification
  requestPasswordReset: (email: string) =>
    post<{ detail: string }>("/api/v1/auth/password-reset/request", { email }),
  confirmPasswordReset: (token: string, newPassword: string) =>
    post<{ detail: string }>("/api/v1/auth/password-reset/confirm", { token, new_password: newPassword }),
  requestEmailVerification: () =>
    post<{ detail: string }>("/api/v1/auth/verify-email/request", {}),
  confirmEmailVerification: (token: string) =>
    post<{ detail: string }>("/api/v1/auth/verify-email/confirm", { token }),
  updateProfile: (patch: { display_name?: string | null; timezone?: string | null; locale?: string | null }) =>
    put<MePayload>("/api/v1/auth/profile", patch),
  changePassword: (currentPassword: string, newPassword: string) =>
    post<{ detail: string }>("/api/v1/auth/change-password", { current_password: currentPassword, new_password: newPassword }),
  deleteAccount: () =>
    post<{ detail: string }>("/api/v1/auth/delete-account", { confirm_delete: true }),
  cancelDeletion: () =>
    post<{ detail: string }>("/api/v1/auth/cancel-deletion", {}),
  // Phase 13 — personal dashboard. Session-authenticated.
  dashboardSummary: () => get<DashboardSummary>("/api/v1/dashboard/summary"),
  logActivity: (entityType: string, entityId: number, actionType: string) =>
    post<{ logged: boolean }>("/api/v1/dashboard/activity", {
      entity_type: entityType,
      entity_id: entityId,
      action_type: actionType,
    }),
  savePlayer: (playerId: number, category?: string | null) =>
    post<{ saved: boolean; player_id: number }>("/api/v1/dashboard/saved-players", {
      player_id: playerId,
      category: category ?? null,
    }),
  unsavePlayer: (playerId: number) =>
    del<{ removed: boolean }>(`/api/v1/dashboard/saved-players/${playerId}`),
  dismissRecommendation: (playerId: number) =>
    post<{ dismissed: boolean }>("/api/v1/dashboard/dismiss-recommendation", {
      player_id: playerId,
    }),
  // Phase 14 — player archetypes (ML clustering). Public endpoints.
  archetypeOverview: () => get<ArchetypeOverview>("/api/v1/archetypes"),
  archetypeDetail: (clusterId: number, limit = 50) =>
    get<ArchetypeDetail>(`/api/v1/archetypes/${clusterId}${qs({ limit })}`),
  playerArchetype: (playerId: number) =>
    get<PlayerArchetype>(`/api/v1/archetypes/player/${playerId}`),
  // Phase 15 — Transfer Intelligence
  valuationComparison: (playerId: number) =>
    get<ValuationComparison>(`/api/v1/transfers/valuation/${playerId}`),
  undervaluedPlayers: (params: {
    league_id?: number;
    position_group?: string;
    threshold?: number;
    limit?: number;
  }) => get<ValuationGapPlayer[]>(`/api/v1/transfers/undervalued${qs(params)}`),
  overvaluedPlayers: (params: {
    league_id?: number;
    position_group?: string;
    threshold?: number;
    limit?: number;
  }) => get<ValuationGapPlayer[]>(`/api/v1/transfers/overvalued${qs(params)}`),
  transferCandidates: (params: {
    position_group?: string;
    min_age?: number;
    max_age?: number;
    league_id?: number;
    min_value?: number;
    max_value?: number;
    contract_expiring?: boolean;
    min_minutes?: number;
    limit?: number;
  }) => get<TransferCandidateResult>(`/api/v1/transfers/candidates${qs({
    ...params,
    contract_expiring: params.contract_expiring !== undefined ? (params.contract_expiring ? "true" : "false") : undefined,
  })}`),
  candidateTemplates: () =>
    get<{ templates: CandidateTemplate[] }>("/api/v1/transfers/templates"),
  hiddenGems: (params?: {
    min_stat_percentile?: number;
    max_market_value?: number;
    limit?: number;
  }) => get<{ opportunities: OpportunityCard[] }>(`/api/v1/transfers/opportunities/hidden-gems${qs(params ?? {})}`),
  ageOpportunities: (params?: {
    max_age?: number;
    min_stat_percentile?: number;
    limit?: number;
  }) => get<{ opportunities: OpportunityCard[] }>(`/api/v1/transfers/opportunities/age-opportunity${qs(params ?? {})}`),
  transferRisk: (playerId: number, params?: {
    target_league_tier?: string;
    target_position_group?: string;
  }) => get<TransferRisk>(`/api/v1/transfers/risk/${playerId}${qs(params ?? {})}`),
  valuationConfidence: (playerId: number) =>
    get<ValuationConfidence>(`/api/v1/transfers/confidence/${playerId}`),
  positionScarcity: (params?: {
    min_stat_percentile?: number;
    limit?: number;
  }) => get<{ opportunities: PositionScarcityOpportunity[] }>(`/api/v1/transfers/opportunities/position-scarcity${qs(params ?? {})}`),
  // Phase 16 — Organizations
  listOrganizations: () => get<OrgSummary[]>("/api/v1/orgs"),
  createOrganization: (name: string, opts?: { slug?: string; country?: string }) =>
    post<OrgSummary>("/api/v1/orgs", { name, ...opts }),
  getOrganization: (orgId: number) => get<OrgDetail>(`/api/v1/orgs/${orgId}`),
  inviteMember: (orgId: number, email: string, role: string) =>
    post<OrgInviteResult>(`/api/v1/orgs/${orgId}/invite`, { email, role }),
  acceptInvite: (orgId: number, token: string) =>
    post<OrgJoinResult>(`/api/v1/orgs/${orgId}/accept-invite`, { token }),
  listMembers: (orgId: number) => get<OrgMember[]>(`/api/v1/orgs/${orgId}/members`),
  changeRole: (orgId: number, userId: number, role: string) =>
    post<{ changed: boolean }>(`/api/v1/orgs/${orgId}/members/${userId}/role`, { role }),
  removeMember: (orgId: number, userId: number) =>
    post<{ removed: boolean }>(`/api/v1/orgs/${orgId}/members/${userId}/remove`, {}),
  getOrgSettings: (orgId: number) => get<OrgSettings>(`/api/v1/orgs/${orgId}/settings`),
  updateOrgSettings: (orgId: number, patch: Partial<OrgSettings>) =>
    put<OrgSettings>(`/api/v1/orgs/${orgId}/settings`, patch),
  getAuditLog: (orgId: number, params?: { limit?: number; offset?: number }) =>
    get<AuditEntry[]>(`/api/v1/orgs/${orgId}/audit${qs(params ?? {})}`),
  // Phase 16 — Comments
  listComments: (resourceType: string, resourceId: number, orgId: number) =>
    get<Comment[]>(`/api/v1/comments/${resourceType}/${resourceId}${qs({ org_id: orgId })}`),
  addComment: (resourceType: string, resourceId: number, orgId: number, text: string, parentId?: number) =>
    post<{ comment_id: number }>(`/api/v1/comments/${resourceType}/${resourceId}${qs({ org_id: orgId })}`,
      { text, parent_id: parentId ?? null }),
  // Phase 17 — Tactical Intelligence
  tacticalOverview: (matchId: string) =>
    get<TacticalOverview>(`/api/v1/tactical/matches/${matchId}/overview`),
  passingNetwork: (matchId: string, params?: { phase?: string; minute_start?: number; minute_end?: number }) =>
    get<PassingNetworkResult>(`/api/v1/tactical/matches/${matchId}/passing-network${qs(params ?? {})}`),
  pressureMap: (matchId: string) =>
    get<PressureMap>(`/api/v1/tactical/matches/${matchId}/pressure-map`),
  possessionMap: (matchId: string) =>
    get<PossessionMap>(`/api/v1/tactical/matches/${matchId}/possession-map`),
  pressureSuccess: (matchId: string) =>
    get<Record<string, unknown>>(`/api/v1/tactical/matches/${matchId}/pressure-success`),
  formation: (matchId: string, params?: { window_minutes?: number }) =>
    get<FormationResult>(`/api/v1/tactical/matches/${matchId}/formation${qs(params ?? {})}`),
  tacticalCoverage: (matchId: string) =>
    get<{ has_coverage: boolean; event_count: number; message: string }>(`/api/v1/tactical/matches/${matchId}/coverage`),
  // Phase 18 — Internal Analytics
  trackEvent: (eventName: string, properties: Record<string, unknown>, sessionId?: string) =>
    post<{ status: string; event_id: number }>("/api/v1/analytics/events", {
      event_name: eventName, properties, session_id: sessionId,
    }),
  eventSchema: () => get<{ events: Record<string, { required_properties: string[] }> }>('/api/v1/analytics/events/schema'),
  analyticsDau: (date?: string) => get<DauResult>(`/api/v1/analytics/metrics/dau${qs(date ? { date } : {})}`),
  analyticsMau: (date?: string) => get<MauResult>(`/api/v1/analytics/metrics/mau${qs(date ? { date } : {})}`),
  analyticsFeatures: (date?: string) => get<FeatureUsageResult[]>(`/api/v1/analytics/metrics/features${qs(date ? { date } : {})}`),
  analyticsConversion: (start?: string, end?: string) =>
    get<ConversionFunnel>(`/api/v1/analytics/metrics/conversion${qs({ start, end })}`),
  analyticsRetention: (cohortMonth?: string) =>
    get<RetentionCohort[]>(`/api/v1/analytics/metrics/retention${qs(cohortMonth ? { cohort_month: cohortMonth } : {})}`),
  analyticsChurn: (date?: string) => get<ChurnResult>(`/api/v1/analytics/metrics/churn${qs(date ? { date } : {})}`),
  analyticsArpu: (date?: string) => get<ArpuResult>(`/api/v1/analytics/metrics/arpu${qs(date ? { date } : {})}`),
  executiveDashboard: () => get<ExecutiveDashboard>('/api/v1/analytics/dashboard/executive'),
  productDashboard: () => get<{ feature_usage: FeatureUsageResult[]; conversion: ConversionFunnel }>('/api/v1/analytics/dashboard/product'),
  operationsDashboard: () => get<{ error_rate_pct: number; total_events_24h: number; error_events_24h: number }>('/api/v1/analytics/dashboard/operations'),
  cohortDashboard: (cohortMonth?: string) =>
    get<{ retention: RetentionCohort[] }>(`/api/v1/analytics/dashboard/cohorts${qs(cohortMonth ? { cohort_month: cohortMonth } : {})}`),
  analyticsAlerts: (limit?: number) => get<{ alerts: AnalyticsAlert[]; total: number }>(`/api/v1/analytics/alerts${qs(limit ? { limit } : {})}`),
  checkAlerts: () => post<{ alerts_fired: number; alerts: { alert_name: string; message: string }[] }>('/api/v1/analytics/alerts/check', {}),
  analyticsAnomalies: (metricName?: string) =>
    get<AnomalyResult>(`/api/v1/analytics/anomalies${qs(metricName ? { metric_name: metricName } : {})}`),
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

async function put<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "PUT",
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
