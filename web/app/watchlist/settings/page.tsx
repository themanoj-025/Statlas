import type { Metadata } from "next";
import { PreferencesClient } from "./PreferencesClient";

export const metadata: Metadata = {
  title: "Notification settings",
  description: "Control how Statlas alerts you about your watchlist — email on/off, per-trigger-type preferences, and digest frequency.",
  alternates: { canonical: "/watchlist/settings" },
};

export default function PreferencesPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Watchlist</p>
      <h1 className="page__title">Notification settings</h1>
      <p className="page__lede">
        Your preferences are honored absolutely: if a trigger type or channel is off, Statlas
        never sends email for it. Alerts still appear in-app so you never lose data.
      </p>
      <PreferencesClient />
    </div>
  );
}
