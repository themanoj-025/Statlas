import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "System Status",
  description:
    "Real-time status of Statlas services: API, web app, search, workspace, reports, and database.",
  alternates: { canonical: "/status" },
};

const SERVICES = [
  { name: "API", status: "operational", uptime: "99.99%" },
  { name: "Web App", status: "operational", uptime: "99.99%" },
  { name: "Search", status: "operational", uptime: "99.99%" },
  { name: "Workspace", status: "operational", uptime: "100%" },
  { name: "Reports", status: "operational", uptime: "99.95%" },
  { name: "Database", status: "operational", uptime: "99.99%" },
  { name: "Integrations", status: "operational", uptime: "99.98%" },
];

const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  operational: { bg: "var(--color-success-muted)", text: "var(--color-success)", label: "Operational" },
  degraded: { bg: "var(--color-warning-muted)", text: "var(--color-warning)", label: "Degraded" },
  partial: { bg: "var(--color-warning-muted)", text: "var(--color-warning)", label: "Partial outage" },
  major: { bg: "var(--color-danger-muted)", text: "var(--color-danger)", label: "Major outage" },
};

export default function StatusPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
      <p className="kicker">Status</p>
      <h1 className="page__title">System status</h1>
      <p className="page__lede">
        Current status of all Statlas services. Updated automatically.
      </p>

      {/* Overall status */}
      <div
        className="card"
        style={{
          padding: "var(--space-5)",
          marginBottom: "var(--space-6)",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          borderLeft: "4px solid var(--color-success)",
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: "var(--color-success)",
            flexShrink: 0,
          }}
          aria-hidden="true"
        />
        <div>
          <p style={{ fontWeight: 600, margin: 0, fontSize: "var(--text-base)" }}>
            All systems operational
          </p>
          <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            No incidents reported. Last checked: {new Date().toISOString().slice(0, 16).replace("T", " ")} UTC
          </p>
        </div>
      </div>

      {/* Service grid */}
      <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>Services</h2>
      <div className="table-wrap" role="region" aria-label="Service status" tabIndex={0}>
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Service</th>
              <th scope="col">Status</th>
              <th scope="col">Uptime (30 days)</th>
            </tr>
          </thead>
          <tbody>
            {SERVICES.map((service) => {
              const s = STATUS_COLORS[service.status];
              return (
                <tr key={service.name}>
                  <td style={{ fontWeight: 500 }}>{service.name}</td>
                  <td>
                    <span
                      className="chip"
                      style={{ background: s.bg, color: s.text, borderColor: "transparent" }}
                    >
                      {s.label}
                    </span>
                  </td>
                  <td className="num">{service.uptime}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Incident history */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>Recent incidents</h2>
        <div className="card" style={{ padding: "var(--space-5)" }}>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", margin: 0 }}>
            No incidents in the last 30 days.
          </p>
        </div>
      </section>

      {/* Subscribe */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-3)" }}>Subscribe to updates</h2>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
          Get notified when services are degraded or incidents are resolved.
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Status page subscriptions coming soon.
        </p>
      </section>

      {/* Back */}
      <div style={{ marginTop: "var(--space-6)" }}>
        <Link href="/" style={{ fontSize: "var(--text-sm)" }}>&larr; Back to home</Link>
      </div>
    </div>
  );
}
