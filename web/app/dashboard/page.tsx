import type { Metadata } from "next";
import { DashboardClient } from "./DashboardClient";

export const metadata: Metadata = {
  title: "Dashboard — Statlas",
  description:
    "Your personal scouting dashboard: recently viewed players, saved bookmarks, trending players, and personalized recommendations.",
};

export default function DashboardPage() {
  return <DashboardClient />;
}
