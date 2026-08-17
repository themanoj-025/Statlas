import type { Metadata } from "next";
import { ReportsClient } from "./ReportsClient";

export const metadata: Metadata = {
  title: "Scouting reports",
  description:
    "Your generated AI scouting reports — every claim verified against real Statlas data, with an evidence appendix tracing each figure to its source.",
  alternates: { canonical: "/reports" },
};

export default function ReportsPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-lg)" }}>
      <p className="kicker">Reports</p>
      <h1 className="page__title">Scouting reports</h1>
      <p className="page__lede">
        Reports are generated from verified Statlas data — percentiles, raw stats, Phase 6
        comparables, and your own workspace notes when generated from a shortlist entry. Every
        claim is checked against the data before a report is finalised, and the evidence appendix
        makes each figure traceable to its source.
      </p>
      <ReportsClient />
    </div>
  );
}
