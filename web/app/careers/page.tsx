import type { Metadata } from "next";
import Link from "next/link";
import { MapPin, Clock, DollarSign, Briefcase } from "lucide-react";

export const metadata: Metadata = {
  title: "Careers",
  description:
    "Join the Statlas team. We are building the most transparent football analytics platform. Open positions in engineering, data science, and product.",
  alternates: { canonical: "/careers" },
};

const VALUES = [
  {
    title: "Transparency over mystery",
    description: "We publish our methodology. Every number on the site traces to a documented formula. We apply the same standard to how we work.",
  },
  {
    title: "Honesty over marketing",
    description: "No fabricated numbers, no placeholder data, no inflated claims. If we do not know something, we say so.",
  },
  {
    title: "Depth over breadth",
    description: "We build what we understand deeply. We do not try to do everything — we do a few things well.",
  },
  {
    title: "Users who verify",
    description: "Our users are scouts, analysts, and journalists. They check our numbers. We build for people who read the sport closely.",
  },
];

const OPEN_POSITIONS = [
  {
    title: "Full-Stack Engineer",
    location: "Remote (EU timezone preferred)",
    type: "Full-time",
    description:
      "Build and maintain the Statlas platform — Next.js frontend, FastAPI backend, PostgreSQL data layer. You will work on features that scouts and analysts use daily.",
    requirements: [
      "3+ years with React/Next.js and Python",
      "Experience with PostgreSQL and data-intensive applications",
      "Interest in football analytics (not required, but helpful)",
    ],
  },
  {
    title: "Data Engineer",
    location: "Remote (EU timezone preferred)",
    type: "Full-time",
    description:
      "Maintain and extend the data pipeline — scraper reliability, anomaly detection, percentile computation, and data quality enforcement.",
    requirements: [
      "3+ years with Python and data pipelines",
      "Experience with web scraping, HTML parsing, and API integration",
      "Understanding of statistical concepts (percentiles, distributions)",
    ],
  },
  {
    title: "Product Designer",
    location: "Remote",
    type: "Full-time",
    description:
      "Design clear, accessible interfaces for data-dense workflows. Radar charts, trend charts, data tables, and scouting tools.",
    requirements: [
      "3+ years designing data-heavy applications",
      "Strong understanding of accessibility (WCAG AA)",
      "Portfolio showing complex UI work",
    ],
  },
];

export default function CareersPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Careers</p>
      <h1 className="page__title">Join Statlas</h1>
      <p className="page__lede">
        We are building the most transparent football analytics platform. If you want to
        work on tools where every number has to survive scrutiny, we want to hear from you.
      </p>

      {/* Mission */}
      <section className="card" style={{ padding: "var(--space-6)", marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-3)" }}>Why Statlas</h2>
        <p style={{ color: "var(--color-text-secondary)", maxWidth: "60ch" }}>
          Most analytics tools hide their formulas. Ours is published as code. We are a small
          team building a product for people who already understand the sport deeply \u2014
          scouts, analysts, agents, and journalists who verify claims before acting on them.
        </p>
      </section>

      {/* Values */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Our values</h2>
        <div className="grid">
          {VALUES.map((v) => (
            <div key={v.title} className="card grid__span-6" style={{ padding: "var(--space-5)" }}>
              <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-2)" }}>{v.title}</h3>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", margin: 0 }}>
                {v.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Open positions */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Open positions</h2>
        <div style={{ display: "grid", gap: "var(--space-4)" }}>
          {OPEN_POSITIONS.map((pos) => (
            <div key={pos.title} className="card" style={{ padding: "var(--space-5)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
                <div>
                  <h3 style={{ fontSize: "var(--text-lg)", margin: 0 }}>{pos.title}</h3>
                  <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-1)", fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                      <MapPin size={14} aria-hidden="true" /> {pos.location}
                    </span>
                    <span style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                      <Clock size={14} aria-hidden="true" /> {pos.type}
                    </span>
                  </div>
                </div>
                <a href="mailto:careers@statlas.com" className="button button--sm">
                  Apply
                </a>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>
                {pos.description}
              </p>
              <p style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--space-2)" }}>Requirements:</p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {pos.requirements.map((r) => (
                  <li key={r} style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", padding: "var(--space-1) 0" }}>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Benefits */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Benefits</h2>
        <div className="card" style={{ padding: "var(--space-5)" }}>
          <div className="grid">
            {[
              "Remote-first (EU timezone preferred)",
              "Competitive salary",
              "Professional development budget",
              "Flexible working hours",
              "30 days paid time off",
              "Equipment budget",
            ].map((benefit) => (
              <div key={benefit} className="grid__span-3" style={{ padding: "var(--space-2) 0", fontSize: "var(--text-sm)" }}>
                {benefit}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: "var(--space-6)", textAlign: "center", background: "var(--color-surface-raised)", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Ready to apply?</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Send your CV and a short note about why Statlas interests you.
        </p>
        <a href="mailto:careers@statlas.com" className="button">
          careers@statlas.com
        </a>
      </section>
    </div>
  );
}
