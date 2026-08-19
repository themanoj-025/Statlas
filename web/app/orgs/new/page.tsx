import type { Metadata } from "next";
import { CreateOrgClient } from "./CreateOrgClient";

export const metadata: Metadata = {
  title: "Create Organization — Statlas",
  description: "Create a new scouting organization to collaborate with your team.",
};

export default function NewOrgPage() {
  return (
    <div className="container page">
      <p className="kicker">Team Management</p>
      <h1 className="page__title">Create Organization</h1>
      <p className="page__lede">
        Set up a scouting organization to share shortlists, reports, and transfer
        intelligence with your team.
      </p>

      <CreateOrgClient />
    </div>
  );
}
