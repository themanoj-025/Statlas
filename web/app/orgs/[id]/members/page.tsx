import type { Metadata } from "next";
import Link from "next/link";
import { api } from "@/lib/api";
import { MembersClient } from "./MembersClient";

export const metadata: Metadata = {
  title: "Members — Statlas",
  description: "Manage organization members and roles.",
};

export default async function MembersPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const orgId = parseInt(id, 10);

  let org, members;
  try {
    [org, members] = await Promise.all([
      api.getOrganization(orgId),
      api.listMembers(orgId),
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
        <Link href={`/orgs/${orgId}`}>{org.name}</Link> · Members
      </p>
      <h1 className="page__title">Team Members</h1>
      <p className="page__lede">
        {org.member_count} member{org.member_count !== 1 ? "s" : ""} · {org.tier} plan
      </p>

      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        <Link href={`/orgs/${orgId}`} className="button button--secondary button--sm">
          Overview
        </Link>
        <Link href={`/orgs/${orgId}/members`} className="button button--primary button--sm">
          Members
        </Link>
        <Link href={`/orgs/${orgId}/settings`} className="button button--secondary button--sm">
          Settings
        </Link>
        <Link href={`/orgs/${orgId}/audit`} className="button button--secondary button--sm">
          Audit Log
        </Link>
      </div>

      <MembersClient orgId={orgId} initialMembers={members} orgTier={org.tier} />
    </div>
  );
}
