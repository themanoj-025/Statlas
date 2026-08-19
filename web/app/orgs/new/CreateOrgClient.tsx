"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";

export function CreateOrgClient() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [country, setCountry] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const autoSlug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 128);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const org = await api.createOrganization(name.trim(), {
        slug: slug.trim() || undefined,
        country: country.trim() || undefined,
      });
      router.push(`/orgs/${org.org_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create organization");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 480 }}>
      <div style={{ display: "grid", gap: "16px" }}>
        <div>
          <label className="field__label" htmlFor="org-name">
            Organization Name *
          </label>
          <input
            id="org-name"
            type="text"
            className="input"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slug) setSlug(autoSlug);
            }}
            placeholder="e.g. Juventus Scouting Department"
            disabled={loading}
            autoFocus
          />
        </div>

        <div>
          <label className="field__label" htmlFor="org-slug">
            URL Slug
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
              statlas.com/orgs/
            </span>
            <input
              id="org-slug"
              type="text"
              className="input"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder={autoSlug || "organization-slug"}
              disabled={loading}
              style={{ flex: 1 }}
            />
          </div>
          <p style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", marginTop: "4px" }}>
            Leave blank to auto-generate from the name.
          </p>
        </div>

        <div>
          <label className="field__label" htmlFor="org-country">
            Country
          </label>
          <input
            id="org-country"
            type="text"
            className="input"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="e.g. Italy"
            disabled={loading}
          />
        </div>
      </div>

      {error && (
        <p style={{ marginTop: "12px", fontSize: "0.85rem", color: "var(--color-negative, #ef4444)" }}>
          {error}
        </p>
      )}

      <div style={{ marginTop: "24px", display: "flex", gap: "8px" }}>
        <button
          type="button"
          className="button button--primary"
          onClick={() => void handleSubmit()}
          disabled={loading || !name.trim()}
        >
          {loading ? "Creating…" : "Create Organization"}
        </button>
      </div>

      <div
        style={{
          marginTop: "24px",
          padding: "16px",
          border: "1px solid var(--color-border, #e5e7eb)",
          borderRadius: "8px",
          fontSize: "0.85rem",
        }}
      >
        <h3 style={{ margin: "0 0 8px" }}>What happens next?</h3>
        <ul style={{ margin: 0, paddingLeft: "16px" }}>
          <li>You become the organization <strong>owner</strong></li>
          <li>Your existing personal data stays personal (not auto-converted)</li>
          <li>Invite teammates via email from the Members page</li>
          <li>Shared shortlists, reports, and watches are visible to all org members</li>
        </ul>
      </div>
    </div>
  );
}
