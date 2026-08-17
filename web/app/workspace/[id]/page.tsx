import type { Metadata } from "next";
import { ShortlistClient } from "./ShortlistClient";

export const metadata: Metadata = {
  title: "Shortlist",
  description:
    "A scouting shortlist — players, notes, tags, priorities and the status pipeline history.",
  robots: { index: false, follow: false },
};

export default function ShortlistPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-lg)" }}>
      <ShortlistClient />
    </div>
  );
}
