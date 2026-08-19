import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import { SettingsClient } from "./SettingsClient";

export const metadata: Metadata = {
  title: "Settings — Statlas",
  description: "Organization settings and configuration.",
};

export default async function OrgSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const orgId = parseInt(id, 10);

  let org, settings;
  try {
    [org, settings] = await Promise.all([
      api.getOrganization(orgId),
      api.getOrgSettings(orgId),
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

  return (
    <div className="container page">
      <p className="kicker">
        <Link href={`/orgs/${orgId}`}>{org.name}</Link> · Settings
      </p>
      <h1 className="page__title">Organization Settings</h1>

      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <Link href={`/orgs/${orgId}`} className="button button--secondary button--sm">
          Overview
        </Link>
        <Link href={`/orgs/${orgId}/members`} className="button button--secondary button--sm">
          Members
        </Link>
        <Link href={`/orgs/${orgId}/settings`} className="button button--primary button--sm">
          Settings
        </Link>
        <Link href={`/orgs/${orgId}/audit`} className="button button--secondary button--sm">
          Audit Log
        </Link>
      </div>

      <SettingsClient orgId={orgId} initialSettings={settings} />
    </div>
  );
}
