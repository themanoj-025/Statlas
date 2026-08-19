"use client";

import { useCallback, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { OrgMember } from "@/lib/types";

const ROLE_OPTIONS = ["owner", "manager", "scout", "viewer"] as const;

const ROLE_DESCRIPTIONS: Record<string, string> = {
  owner: "Full access — can delete org, manage billing, all member actions",
  manager: "Invite/remove members, manage shared resources, view audit log",
  scout: "Create/edit own resources, comment, view org resources",
  viewer: "Read-only access to org resources",
};

const SEAT_LIMITS: Record<string, number> = {
  free: 5,
  pro: 25,
  enterprise: 100,
};

export function MembersClient({
  orgId,
  initialMembers,
  orgTier,
}: {
  orgId: number;
  initialMembers: OrgMember[];
  orgTier: string;
}) {
  const [members, setMembers] = useState(initialMembers);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("scout");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteResult, setInviteResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await api.listMembers(orgId);
      setMembers(data);
    } catch {
      // ignore
    }
  }, [orgId]);

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    setInviteLoading(true);
    setError(null);
    setInviteResult(null);
    try {
      const result = await api.inviteMember(orgId, inviteEmail.trim(), inviteRole);
      setInviteResult(
        `Invite sent to ${result.email}. Share this link: /orgs/${orgId}/accept?token=${result.raw_token}`
      );
      setInviteEmail("");
      void reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send invite");
    } finally {
      setInviteLoading(false);
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await api.changeRole(orgId, userId, newRole);
      void reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to change role");
    }
  };

  const handleRemove = async (userId: number) => {
    if (!confirm("Remove this member? They will lose access to shared resources.")) return;
    try {
      await api.removeMember(orgId, userId);
      void reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove member");
    }
  };

  const maxSeats = SEAT_LIMITS[orgTier] ?? 5;
  const atLimit = members.length >= maxSeats;

  return (
    <div>
      {/* Invite form */}
      <div
        style={{
          padding: "16px",
          border: "1px solid var(--color-border, #e5e7eb)",
          borderRadius: "8px",
          marginBottom: "24px",
        }}
      >
        <h3 style={{ margin: "0 0 12px" }}>Invite Member</h3>
        {atLimit && (
          <p style={{ color: "var(--color-warning, #f59e0b)", fontSize: "0.85rem", margin: "0 0 8px" }}>
            This organization has reached its {maxSeats}-seat limit. Upgrade to add more members.
          </p>
        )}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <input
            type="email"
            placeholder="Email address"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            disabled={inviteLoading || atLimit}
            className="input"
            style={{ flex: "1 1 200px" }}
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value)}
            disabled={inviteLoading || atLimit}
            className="select"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <button
            type="button"
            className="button button--primary"
            onClick={() => void handleInvite()}
            disabled={inviteLoading || atLimit || !inviteEmail.trim()}
          >
            {inviteLoading ? "Sending…" : "Invite"}
          </button>
        </div>
        {inviteResult && (
          <p style={{ marginTop: "8px", fontSize: "0.8rem", color: "var(--color-positive, #22c55e)" }}>
            {inviteResult}
          </p>
        )}
        {error && (
          <p style={{ marginTop: "8px", fontSize: "0.8rem", color: "var(--color-negative, #ef4444)" }}>
            {error}
          </p>
        )}
      </div>

      {/* Role legend */}
      <div
        style={{
          padding: "12px 16px",
          border: "1px solid var(--color-border, #e5e7eb)",
          borderRadius: "8px",
          marginBottom: "24px",
          fontSize: "0.8rem",
        }}
      >
        <h4 style={{ margin: "0 0 8px" }}>Role Permissions</h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "8px" }}>
          {Object.entries(ROLE_DESCRIPTIONS).map(([role, desc]) => (
            <div key={role}>
              <strong>{role}</strong>: {desc}
            </div>
          ))}
        </div>
      </div>

      {/* Members table */}
      {members.length === 0 ? (
        <div className="empty-state">
          <p>No members yet. Invite your team to start collaborating.</p>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Role</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
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
                  <select
                    value={m.role}
                    onChange={(e) => void handleRoleChange(m.user_id, e.target.value)}
                    className="select"
                    style={{ fontSize: "0.8rem", padding: "4px 8px" }}
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </td>
                <td style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                  {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"}
                </td>
                <td>
                  {m.role !== "owner" && (
                    <button
                      type="button"
                      className="button button--sm button--ghost"
                      style={{ color: "var(--color-negative, #ef4444)" }}
                      onClick={() => void handleRemove(m.user_id)}
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
