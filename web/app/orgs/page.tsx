import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import type { OrgSummary } from "@/lib/types";

export const metadata: Metadata = {
  title: "Organizations — Statlas",
  description: "Manage your scouting organizations and team collaboration.",
};

export default async function OrgsPage() {
  let orgs: OrgSummary[] = [];
  try {
    orgs = await api.listOrganizations();
  } catch {
    orgs = [];
  }

  return (
    <div className="container page">
      <p className="kicker">Team Management</p>
      <h1 className="page__title">Organizations</h1>
      <p className="page__lede">
        Manage your scouting teams and collaborate on transfer decisions.
        Organizations let multiple users share shortlists, reports, and watches.
      </p>

      <div className="section-head">
        <h2>Your Organizations</h2>
        <Link href="/orgs/new" className="button button--primary button--sm">
          Create Organization
        </Link>
      </div>

      {orgs.length === 0 ? (
        <div className="empty-state">
          <p>You haven&rsquo;t joined any organizations yet.</p>
          <p style={{ marginTop: "8px", color: "var(--color-text-secondary)" }}>
            Create an organization to start collaborating with your scouting team,
            or ask a teammate for an invite link.
          </p>
          <Link href="/orgs/new" className="button button--primary" style={{ marginTop: "16px" }}>
            Create Your First Organization
          </Link>
        </div>
      ) : (
        <div className="grid">
          {orgs.map((org) => (
            <Link
              key={org.org_id}
              href={`/orgs/${org.org_id}`}
              className="position-card grid__span-3"
            >
              <span className="position-card__code">
                {org.tier === "pro" ? "⭐" : org.tier === "enterprise" ? "🏢" : "⚽"}
              </span>
              <span className="position-card__name">{org.name}</span>
              <span className="position-card__meta">
                Role: {org.role} · Plan: {org.tier}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
