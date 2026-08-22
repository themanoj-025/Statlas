import type { Metadata } from "next";
import Link from "next/link";
import { Smartphone, Search, Bell, FolderOpen, BarChart3 } from "lucide-react";

export const metadata: Metadata = {
  title: "Mobile",
  description:
    "Statlas on mobile. Quick player search, watchlist notifications, and shortlist management from your phone.",
  alternates: { canonical: "/mobile" },
};

const MOBILE_FEATURES = [
  { icon: Search, title: "Quick search", desc: "Find any qualifying player by name or criteria" },
  { icon: Bell, title: "Push notifications", desc: "Get alerts when watched players move in percentiles" },
  { icon: FolderOpen, title: "Shortlist management", desc: "Add players, update status, and add notes on the go" },
  { icon: BarChart3, title: "Radar comparisons", desc: "Compare players side-by-side with touch-friendly controls" },
];

export default function MobilePage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Mobile</p>
      <h1 className="page__title">Statlas on your phone</h1>
      <p className="page__lede">
        Access football analytics from anywhere. Quick search, notifications, and
        shortlist management from your pocket.
      </p>

      <div className="notice" style={{ marginBottom: "var(--space-6)" }}>
        <strong>Coming soon.</strong> The Statlas mobile app is in development. The full web
        platform is available on mobile browsers with a responsive layout.
      </div>

      {/* Features */}
      <div className="grid" style={{ marginBottom: "var(--space-6)" }}>
        {MOBILE_FEATURES.map((f) => {
          const Icon = f.icon;
          return (
            <div key={f.title} className="card grid__span-6" style={{ padding: "var(--space-5)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
                <h3 style={{ fontSize: "var(--text-base)", margin: 0 }}>{f.title}</h3>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", margin: 0 }}>{f.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Feature comparison */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Web vs Mobile</h2>
        <div className="table-wrap" role="region" aria-label="Feature comparison" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Feature</th>
                <th scope="col">Web</th>
                <th scope="col">Mobile</th>
              </tr>
            </thead>
            <tbody>
              {[
                { feature: "Player profiles", web: true, mobile: true },
                { feature: "Radar comparisons", web: true, mobile: true },
                { feature: "Trend charts", web: true, mobile: true },
                { feature: "Shot/pass maps", web: true, mobile: true },
                { feature: "Search", web: true, mobile: true },
                { feature: "Workspace", web: true, mobile: true },
                { feature: "Reports", web: true, mobile: true },
                { feature: "Push notifications", web: false, mobile: true },
                { feature: "Offline mode", web: false, mobile: false },
              ].map((row) => (
                <tr key={row.feature}>
                  <td>{row.feature}</td>
                  <td className="num">{row.web ? "Yes" : "\u2014"}</td>
                  <td className="num">{row.mobile ? "Yes" : "Coming"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Beta signup */}
      <section
        className="card"
        style={{ padding: "var(--space-6)", textAlign: "center" }}
      >
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>
          Get notified when the app launches
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Enter your email to be notified when the mobile app is available for download.
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Email notifications coming soon. In the meantime, the web version works great on mobile browsers.
        </p>
      </section>
    </div>
  );
}
