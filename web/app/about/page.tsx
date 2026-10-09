import type { Metadata } from "next";
import Link from "next/link";
import { Target, Eye, Shield, Users, Calendar, Mail } from "lucide-react";

export const metadata: Metadata = {
  title: "About Statlas — an analytics platform that shows its work",
  description:
    "Why Statlas exists: football analytics that publishes its formulas instead of hiding them behind a black box. What the product is, what it is not, and how it is built.",
  alternates: { canonical: "/about" },
};

const VALUES = [
  {
    icon: Shield,
    title: "Transparency",
    desc: "Every metric has a published formula. The methodology page is generated from the same registry the code reads.",
  },
  {
    icon: Target,
    title: "Honesty",
    desc: "Missing data is marked, not guessed. Gaps are gaps. Numbers are never fabricated, even in demos.",
  },
  {
    icon: Eye,
    title: "Auditability",
    desc: "Every stat block carries its snapshot date. Historical data is append-only and never overwritten.",
  },
  {
    icon: Users,
    title: "Community",
    desc: "Built for people who read the sport closely — scouts, analysts, agents, and journalists who verify claims.",
  },
];

const TIMELINE = [
  { date: "March 2025", event: "Statlas founded" },
  { date: "July 2025", event: "First release — player profiles, radar comparisons, leaderboards" },
  { date: "August 2025", event: "Trend analysis and shot/pass maps added" },
  { date: "October 2025", event: "Workspace and structured search launched" },
  { date: "January 2026", event: "AI scouting reports with verification gate" },
  { date: "March 2026", event: "Watchlist, alerts, and API access" },
  { date: "June 2026", event: "Player archetypes and transfer intelligence" },
  { date: "August 2026", event: "Hardening closeout — accessibility, performance, security CI" },
];

export default function AboutPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">About</p>
      <h1 className="page__title">Statlas shows its work</h1>
      <p className="page__lede">
        A football data platform for people who already read the sport closely. Every number
        traces to a published formula. No black box, no fabricated numbers.
      </p>

      {/* Mission */}
      <section className="card" style={{ padding: "var(--space-6)", marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-3)" }}>Mission</h2>
        <p style={{ color: "var(--color-text-secondary)", maxWidth: "60ch", marginBottom: "var(--space-4)" }}>
          To bring transparency to football analytics. A world where every statistic is grounded
          in published methodology, and users can verify the numbers themselves.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
          <div>
            <h3 style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-1)" }}>What Statlas is</h3>
            <ul style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", paddingLeft: "var(--space-4)" }}>
              <li>A per-90 statistics platform with published methodology</li>
              <li>A tool for scouts, analysts, agents, and media</li>
              <li>Built on real data from FBref, Understat, and StatsBomb</li>
            </ul>
          </div>
          <div>
            <h3 style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-1)" }}>What Statlas is not</h3>
            <ul style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", paddingLeft: "var(--space-4)" }}>
              <li>Not a prediction tool — it measures this season&apos;s output</li>
              <li>Not a live data service — statistics refresh weekly</li>
              <li>Not a black box — every formula is published</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Values */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Values</h2>
        <div className="grid">
          {VALUES.map((v) => {
            const Icon = v.icon;
            return (
              <div key={v.title} className="card grid__span-6" style={{ padding: "var(--space-5)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                  <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
                  <h3 style={{ fontSize: "var(--text-base)", margin: 0 }}>{v.title}</h3>
                </div>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", margin: 0 }}>
                  {v.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* How it's built */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-3)" }}>How it is built</h2>
        <div className="prose">
          <p>
            Server-rendered Next.js pages over a versioned FastAPI backend, PostgreSQL for
            structured data, and a modular data-source layer that can swap scraped feeds for a
            licensed feed as revenue justifies it.
          </p>
          <p>
            The engineering standards — tested parsers, append-only snapshots, an anomaly gate
            before anything is published, automated accessibility and performance checks in CI —
            are documented in the project&apos;s public engineering docs, because &ldquo;we take
            data integrity seriously&rdquo; is a claim best made by showing the checks, not by
            asserting them.
          </p>
        </div>
      </section>

      {/* Timeline */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Timeline</h2>
        <div style={{ borderLeft: "2px solid var(--color-border)", paddingLeft: "var(--space-5)" }}>
          {TIMELINE.map((t) => (
            <div key={t.date} style={{ marginBottom: "var(--space-4)", position: "relative" }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "var(--color-primary)",
                  position: "absolute",
                  left: "calc(-1 * var(--space-5) - 6px)",
                  top: 6,
                }}
                aria-hidden="true"
              />
              <div className="num" style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-1)" }}>
                {t.date}
              </div>
              <p style={{ fontSize: "var(--text-sm)", margin: 0 }}>{t.event}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Company stats */}
      <section style={{ marginBottom: "var(--space-6)" }}>
        <div className="grid">
          {[
            { value: "16", label: "tracked metrics" },
            { value: "3", label: "league tiers" },
            { value: "Weekly", label: "data refresh" },
            { value: "Published", label: "methodology" },
          ].map((s) => (
            <div key={s.label} className="card grid__span-3" style={{ padding: "var(--space-4)", textAlign: "center" }}>
              <div className="num" style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: "var(--color-primary)" }}>
                {s.value}
              </div>
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Contact */}
      <section className="card" style={{ padding: "var(--space-5)" }}>
        <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>Contact</h2>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)" }}>
          Found an error in the data? A mismatch between the methodology and a number on the
          site? Something that should work but does not?
        </p>
        <p style={{ fontSize: "var(--text-sm)", margin: 0 }}>
          <a href="mailto:data@statlas.com" style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-1)" }}>
            <Mail size={14} aria-hidden="true" /> data@statlas.com
          </a>{" "}
          — data-accuracy reports are read first.
        </p>
      </section>
    </div>
  );
}
