import type { Metadata } from "next";
import { WorkspaceClient } from "./WorkspaceClient";

export const metadata: Metadata = {
  title: "Workspace",
  description:
    "Your scouting workspace — save players to shortlists, tag and annotate them, and move them through the status pipeline.",
  alternates: { canonical: "/workspace" },
};

export default function WorkspacePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-lg)" }}>
      <p className="kicker">Workspace</p>
      <h1 className="page__title">Scouting workspace</h1>
      <p className="page__lede">
        Track candidates through a real decision process: save players, tag and annotate
        them, set priorities, and move them through the pipeline (discovered → monitoring →
        scouted → shortlisted → reviewed → rejected / signed).
      </p>
      <WorkspaceClient />
    </div>
  );
}
