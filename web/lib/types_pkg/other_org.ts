export type OrgSummary = {
  org_id: number;
  name: string;
  slug: string;
  role: string;
  tier: string;
  joined_at: string | null;
};

export type OrgDetail = {
  org_id: number;
  name: string;
  slug: string;
  tier: string;
  owner_user_id: number;
  member_count: number;
  created_at: string | null;
  country: string | null;
};

export type OrgInviteResult = {
  invite_id: number;
  email: string;
  role: string;
  expires_at: string;
  raw_token: string;
};

export type OrgJoinResult = {
  org_id: number;
  role: string;
  joined_at: string | null;
};

export type OrgSettings = {
  org_id: number;
  data_retention_days: number;
  workspace_name: string | null;
  enable_audit_logging: boolean;
  allow_public_reporting: boolean;
  require_2fa: boolean;
};

export type AuditEntry = {
  id: number;
  action: string;
  performed_by: string;
  performed_by_user_id: number;
  target_user_id: number | null;
  resource_type: string | null;
  resource_id: number | null;
  detail: Record<string, unknown>;
  created_at: string | null;
};
