import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Audit Log — Statlas",
  description: "Organization audit trail for compliance and accountability.",
};

export default async function AuditLogPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const orgId = parseInt(id, 10);

  let org, auditLog;
  try {
    [org, auditLog] = await Promise.all([
      api.getOrganization(orgId),
      api.getAuditLog(orgId, { limit: 100 }),
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

  const actionLabels: Record<string, string> = {
    user_added: "Member added",
    user_removed: "Member removed",
    role_changed: "Role changed",
    resource_created: "Resource created",
    resource_shared: "Resource shared",
    resource_deleted: "Resource deleted",
    comment_added: "Comment added",
  };

  return (
    <div className="container page">
      <p className="kicker">
        <Link href={`/orgs/${orgId}`}>{org.name}</Link> · Audit Log
      </p>
      <h1 className="page__title">Audit Log</h1>
      <p className="page__lede">
        Append-only trail of team changes for compliance and accountability.
      </p>

      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <Link href={`/orgs/${orgId}`} className="button button--secondary button--sm">
          Overview
        </Link>
        <Link href={`/orgs/${orgId}/members`} className="button button--secondary button--sm">
          Members
        </Link>
        <Link href={`/orgs/${orgId}/settings`} className="button button--secondary button--sm">
          Settings
        </Link>
        <Link href={`/orgs/${orgId}/audit`} className="button button--primary button--sm">
          Audit Log
        </Link>
      </div>

      {auditLog.length === 0 ? (
        <div className="empty-state">
          <p>No audit entries yet. Team activity will appear here as members are added and resources change.</p>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Performed By</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLog.map((entry) => (
              <tr key={entry.id}>
                <td style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", whiteSpace: "nowrap" }}>
                  {entry.created_at ? new Date(entry.created_at).toLocaleString() : "—"}
                </td>
                <td>
                  <span className="badge badge--sm" style={{ fontSize: "0.75rem" }}>
                    {actionLabels[entry.action] ?? entry.action}
                  </span>
                </td>
                <td style={{ fontSize: "0.85rem" }}>{entry.performed_by}</td>
                <td style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                  {Object.keys(entry.detail).length > 0
                    ? Object.entries(entry.detail)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(", ")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
