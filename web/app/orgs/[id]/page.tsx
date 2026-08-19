import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Organization — Statlas",
  description: "Organization details, members, and settings.",
};

export default async function OrgDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const orgId = parseInt(id, 10);

  let org, members, settings;
  try {
    [org, members, settings] = await Promise.all([
      api.getOrganization(orgId),
      api.listMembers(orgId),
      api.getOrgSettings(orgId).catch(() => null),
    ]);
  } catch {
    return (
      <div className="container page">
        <div className="empty-state">
          <p>Organization not found or you don&rsquo;t have access.</p>
          <Link href="/orgs" className="button button--primary" style={{ marginTop: "16px" }}>
            Back to Organizations
          </Link>
        </div>
      </div>
    );
  }

  const roleColors: Record<string, string> = {
    owner: "var(--color-positive, #22c55e)",
    manager: "var(--color-warning, #f59e0b)",
    scout: "var(--color-text-secondary)",
    viewer: "var(--color-text-tertiary, #9ca3af)",
  };

  return (
    <div className="container page">
      <p className="kicker">Organization</p>
      <h1 className="page__title">{org.name}</h1>
      <p className="page__lede">
        {org.member_count} member{org.member_count !== 1 ? "s" : ""} · {org.tier} plan
        {org.country ? ` · ${org.country}` : ""}
      </p>

      {/* Tabs */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <Link
          href={`/orgs/${orgId}`}
          className="button button--primary button--sm"
        >
          Overview
        </Link>
        <Link
          href={`/orgs/${orgId}/members`}
          className="button button--secondary button--sm"
        >
          Members
        </Link>
        <Link
          href={`/orgs/${orgId}/settings`}
          className="button button--secondary button--sm"
        >
          Settings
        </Link>
        <Link
          href={`/orgs/${orgId}/audit`}
          className="button button--secondary button--sm"
        >
          Audit Log
        </Link>
      </div>

      {/* Members preview */}
      <div className="section-head">
        <h2>Team Members</h2>
        <Link href={`/orgs/${orgId}/members`} style={{ marginLeft: "auto", fontSize: "0.85rem" }}>
          Manage →
        </Link>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Member</th>
            <th>Role</th>
            <th>Joined</th>
          </tr>
        </thead>
        <tbody>
          {members.slice(0, 10).map((m) => (
            <tr key={m.user_id}>
              <td>
                <strong>{m.display_name || m.email}</strong>
                {m.display_name && (
                  <span style={{ marginLeft: "8px", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                    {m.email}
                  </span>
                )}
              </td>
              <td>
                <span
                  className="badge badge--sm"
                  style={{ color: roleColors[m.role] ?? "inherit", fontSize: "0.75rem" }}
                >
                  {m.role}
                </span>
              </td>
              <td style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Quick settings */}
      {settings && (
        <>
          <div className="section-head" style={{ marginTop: "24px" }}>
            <h2>Settings</h2>
            <Link href={`/orgs/${orgId}/settings`} style={{ marginLeft: "auto", fontSize: "0.85rem" }}>
              Edit →
            </Link>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            <div style={{ padding: "16px", border: "1px solid var(--color-border, #e5e7eb)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>Audit Logging</div>
              <div style={{ fontWeight: 600 }}>{settings.enable_audit_logging ? "Enabled" : "Disabled"}</div>
            </div>
            <div style={{ padding: "16px", border: "1px solid var(--color-border, #e5e7eb)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>Data Retention</div>
              <div style={{ fontWeight: 600 }}>{settings.data_retention_days} days</div>
            </div>
            <div style={{ padding: "16px", border: "1px solid var(--color-border, #e5e7eb)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>Require 2FA</div>
              <div style={{ fontWeight: 600 }}>{settings.require_2fa ? "Yes" : "No"}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
