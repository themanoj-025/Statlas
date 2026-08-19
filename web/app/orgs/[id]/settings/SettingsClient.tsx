"use client";

import { useCallback, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { OrgSettings } from "@/lib/types";

export function SettingsClient({
  orgId,
  initialSettings,
}: {
  orgId: number;
  initialSettings: OrgSettings;
}) {
  const [settings, setSettings] = useState(initialSettings);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = useCallback(
    async (patch: Partial<OrgSettings>) => {
      setSaving(true);
      setError(null);
      setSaved(false);
      try {
        const updated = await api.updateOrgSettings(orgId, patch);
        setSettings(updated);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to save settings");
      } finally {
        setSaving(false);
      }
    },
    [orgId]
  );

  return (
    <div>
      {saved && (
        <div
          style={{
            padding: "8px 16px",
            background: "var(--color-positive-muted, #f0fdf4)",
            border: "1px solid var(--color-positive, #22c55e)",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "0.85rem",
          }}
        >
          Settings saved successfully.
        </div>
      )}
      {error && (
        <div
          style={{
            padding: "8px 16px",
            background: "var(--color-negative-muted, #fef2f2)",
            border: "1px solid var(--color-negative, #ef4444)",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {/* General Settings */}
      <section style={{ marginBottom: "32px" }}>
        <h2>General</h2>
        <div style={{ display: "grid", gap: "16px", maxWidth: 480 }}>
          <div>
            <label className="field__label" htmlFor="workspace-name">
              Workspace Name
            </label>
            <input
              id="workspace-name"
              type="text"
              className="input"
              value={settings.workspace_name ?? ""}
              onChange={(e) => setSettings({ ...settings, workspace_name: e.target.value || null })}
              placeholder="e.g. Juventus Scouting Dept"
              disabled={saving}
            />
          </div>
          <div>
            <label className="field__label" htmlFor="retention">
              Data Retention (days)
            </label>
            <input
              id="retention"
              type="number"
              className="input"
              value={settings.data_retention_days}
              onChange={(e) =>
                setSettings({ ...settings, data_retention_days: parseInt(e.target.value, 10) || 90 })
              }
              min={7}
              max={365}
              disabled={saving}
            />
            <p style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", marginTop: "4px" }}>
              How long to keep deleted org data before permanent purge.
            </p>
          </div>
        </div>
      </section>

      {/* Security Settings */}
      <section style={{ marginBottom: "32px" }}>
        <h2>Security</h2>
        <div style={{ display: "grid", gap: "12px", maxWidth: 480 }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={settings.require_2fa}
              onChange={(e) => setSettings({ ...settings, require_2fa: e.target.checked })}
              disabled={saving}
            />
            <span>Require 2FA for all team members</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={settings.enable_audit_logging}
              onChange={(e) => setSettings({ ...settings, enable_audit_logging: e.target.checked })}
              disabled={saving}
            />
            <span>Enable audit logging (recommended for compliance)</span>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={settings.allow_public_reporting}
              onChange={(e) => setSettings({ ...settings, allow_public_reporting: e.target.checked })}
              disabled={saving}
            />
            <span>Allow members to create public-link reports</span>
          </label>
        </div>
      </section>

      {/* Compliance */}
      <section style={{ marginBottom: "32px" }}>
        <h2>Compliance</h2>
        <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
          <p>
            <strong>Data retention:</strong> Deleted org data is purged after {settings.data_retention_days} days.
          </p>
          <p>
            <strong>Audit logging:</strong> {settings.enable_audit_logging ? "All team changes are logged." : "Audit logging is disabled."}
          </p>
          <p style={{ marginTop: "12px" }}>
            See the <a href="/legal">Terms of Service</a> and <a href="/legal">Privacy Policy</a> for data handling details.
          </p>
        </div>
      </section>

      {/* Save button */}
      <div style={{ display: "flex", gap: "8px" }}>
        <button
          type="button"
          className="button button--primary"
          onClick={() =>
            void update({
              workspace_name: settings.workspace_name,
              data_retention_days: settings.data_retention_days,
              require_2fa: settings.require_2fa,
              enable_audit_logging: settings.enable_audit_logging,
              allow_public_reporting: settings.allow_public_reporting,
            })
          }
          disabled={saving}
        >
          {saving ? "Saving…" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
