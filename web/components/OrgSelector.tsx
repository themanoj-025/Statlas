"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, Plus, Building2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { OrgSummary } from "@/lib/types";

/**
 * Organization selector/switcher for the header.
 * Shows current org context and allows switching between personal/org contexts.
 */
export function OrgSelector() {
  const [orgs, setOrgs] = useState<OrgSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Current org from localStorage (null = personal context)
  const [currentOrgId, setCurrentOrgId] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = localStorage.getItem("statlas_org_id");
    return stored ? parseInt(stored, 10) : null;
  });

  const currentOrg = orgs.find((o) => o.org_id === currentOrgId) ?? null;

  const load = useCallback(async () => {
    try {
      const data = await api.listOrganizations();
      setOrgs(data);
    } catch (err) {
      // Non-critical — org features are optional
      if (err instanceof ApiError && err.status === 401) return;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Don't show if user has no orgs and isn't loading
  if (!loading && orgs.length === 0) return null;

  const switchOrg = (orgId: number | null) => {
    setCurrentOrgId(orgId);
    if (orgId === null) {
      localStorage.removeItem("statlas_org_id");
    } else {
      localStorage.setItem("statlas_org_id", String(orgId));
    }
    setOpen(false);
    // Full page reload to clear per-org cached state
    window.location.reload();
  };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        className="button button--sm button--ghost"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.8rem" }}
      >
        <Building2 size={14} aria-hidden="true" />
        {loading ? (
          <span className="skeleton skeleton--text" style={{ width: 80, height: 14 }} />
        ) : currentOrg ? (
          <span style={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {currentOrg.name}
          </span>
        ) : (
          <span>Personal</span>
        )}
        <ChevronDown size={12} aria-hidden="true" />
      </button>

      {open && (
        <div
          role="listbox"
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            marginTop: "4px",
            background: "var(--color-surface, #fff)",
            border: "1px solid var(--color-border, #e5e7eb)",
            borderRadius: "8px",
            padding: "4px",
            minWidth: 200,
            zIndex: 100,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
        >
          {/* Personal context */}
          <button
            type="button"
            role="option"
            aria-selected={currentOrgId === null}
            onClick={() => switchOrg(null)}
            style={{
              display: "block",
              width: "100%",
              textAlign: "left",
              padding: "8px 12px",
              borderRadius: "6px",
              border: "none",
              background: currentOrgId === null ? "var(--color-primary-muted, #f0f4ff)" : "transparent",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            <div style={{ fontWeight: currentOrgId === null ? 600 : 400 }}>My Personal Account</div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
              Solo workspace
            </div>
          </button>

          {/* Org contexts */}
          {orgs.map((org) => (
            <button
              key={org.org_id}
              type="button"
              role="option"
              aria-selected={currentOrgId === org.org_id}
              onClick={() => switchOrg(org.org_id)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "none",
                background: currentOrgId === org.org_id ? "var(--color-primary-muted, #f0f4ff)" : "transparent",
                cursor: "pointer",
                fontSize: "0.85rem",
              }}
            >
              <div style={{ fontWeight: currentOrgId === org.org_id ? 600 : 400 }}>{org.name}</div>
              <div style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)" }}>
                {org.role} · {org.tier}
              </div>
            </button>
          ))}

          {/* Create new org */}
          <Link
            href="/orgs/new"
            onClick={() => setOpen(false)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 12px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              color: "var(--color-text-secondary)",
              textDecoration: "none",
            }}
          >
            <Plus size={14} aria-hidden="true" />
            Create New Org
          </Link>
        </div>
      )}
    </div>
  );
}
