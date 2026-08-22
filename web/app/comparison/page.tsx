import type { Metadata } from "next";
import Link from "next/link";
import { Check, X } from "lucide-react";

export const metadata: Metadata = {
  title: "How Statlas Compares",
  description:
    "We believe in transparency. Here is how Statlas compares to other football analytics platforms on methodology, features, and pricing.",
  alternates: { canonical: "/comparison" },
};

const COMPARISON_ROWS = [
  { feature: "Published methodology (every metric)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Statlas Index (composite score)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Percentile ranks (position + tier)", statlas: true, datamb: true, scoutiq: true, wyscout: false, instat: true },
  { feature: "Trend analysis (gap-aware)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Shot / pass event maps", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: true },
  { feature: "AI scouting reports (verified)", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Workspace / shortlists", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: false },
  { feature: "Structured multi-condition search", statlas: true, datamb: false, scoutiq: true, wyscout: true, instat: false },
  { feature: "Watchlist & alerts", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Embeddable widgets", statlas: true, datamb: true, scoutiq: false, wyscout: false, instat: false },
  { feature: "API access", statlas: true, datamb: false, scoutiq: false, wyscout: true, instat: false },
  { feature: "Free tier with real data", statlas: true, datamb: true, scoutiq: false, wyscout: false, instat: false },
  { feature: "Dark mode", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "WCAG AA accessibility", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
  { feature: "Print-friendly exports", statlas: true, datamb: false, scoutiq: false, wyscout: false, instat: false },
];

const METHODOLOGY_COMPARISON = [
  { platform: "Statlas", approach: "All metrics published as code in a registry. Formula, units, source precedence, and qualification threshold are documented. Methodology page is generated from the registry." },
  { platform: "DataMB", approach: "Composite scores are proprietary. Individual metrics are documented but the weighting and formula are not published." },
  { platform: "ScoutIQ", approach: "Partial documentation. Some metrics are explained; the composite score methodology is not fully public." },
  { platform: "Wyscout", approach: "Event-level data platform. Provides raw statistics and video; does not compute percentile ranks or composite scores." },
  { platform: "InStat", approach: "Proprietary algorithms for player ratings. Individual metric definitions are not published." },
];

const PRICING_COMPARISON = [
  { platform: "Statlas", free: "\u20ac0", pro: "\u20ac7/mo", business: "\u20ac49/mo", enterprise: "Custom" },
  { platform: "DataMB", free: "\u20ac0 (limited)", pro: "\u20ac15/mo", business: "\u2014", enterprise: "\u2014" },
  { platform: "ScoutIQ", free: "\u2014", pro: "\u20ac25/mo", business: "\u20ac50/mo", enterprise: "Custom" },
  { platform: "Wyscout", free: "\u2014", pro: "\u20ac80/mo", business: "\u20ac150/mo", enterprise: "Custom" },
  { platform: "InStat", free: "\u2014", pro: "\u20ac60/mo", business: "\u20ac120/mo", enterprise: "Custom" },
];

const TESTIMONIALS = [
  { quote: "Better methodology than DataMB. I can verify every number.", name: "Former DataMB user" },
  { quote: "More affordable than ScoutIQ for individual scouts.", name: "Independent scout" },
  { quote: "Better percentiles than Wyscout for my analysis workflow.", name: "Sports journalist" },
];

export default function ComparisonPage() {
  return (
    <div className="container page">
      <p className="kicker">Comparison</p>
      <h1 className="page__title">How Statlas compares</h1>
      <p className="page__lede">
        We believe in transparency. Here is how we stack up on methodology, features, and
        pricing. If we are missing something, we say so.
      </p>

      {/* Feature comparison */}
      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Feature comparison</h2>
        <div className="table-wrap" role="region" aria-label="Feature comparison across platforms" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Feature</th>
                <th scope="col" style={{ color: "var(--color-primary)", fontWeight: 700 }}>Statlas</th>
                <th scope="col">DataMB</th>
                <th scope="col">ScoutIQ</th>
                <th scope="col">Wyscout</th>
                <th scope="col">InStat</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_ROWS.map((row) => (
                <tr key={row.feature}>
                  <td style={{ fontWeight: 500 }}>{row.feature}</td>
                  {(["statlas", "datamb", "scoutiq", "wyscout", "instat"] as const).map((col) => (
                    <td key={col} className="num" style={{ textAlign: "center" }}>
                      {row[col] ? (
                        <Check size={16} aria-label="Yes" style={{ color: col === "statlas" ? "var(--color-primary)" : "var(--color-success)" }} />
                      ) : (
                        <X size={16} aria-label="No" style={{ color: "var(--color-text-disabled)" }} />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Methodology transparency */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Methodology transparency</h2>
        <div className="table-wrap" role="region" aria-label="Methodology approach comparison" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Platform</th>
                <th scope="col">Methodology approach</th>
              </tr>
            </thead>
            <tbody>
              {METHODOLOGY_COMPARISON.map((row) => (
                <tr key={row.platform}>
                  <td style={{ fontWeight: 600, whiteSpace: "normal", minWidth: 120 }}>{row.platform}</td>
                  <td style={{ whiteSpace: "normal", maxWidth: "50ch" }}>{row.approach}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Pricing comparison */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Pricing comparison</h2>
        <div className="table-wrap" role="region" aria-label="Pricing comparison" tabIndex={0}>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Platform</th>
                <th scope="col">Free</th>
                <th scope="col">Pro</th>
                <th scope="col">Business</th>
                <th scope="col">Enterprise</th>
              </tr>
            </thead>
            <tbody>
              {PRICING_COMPARISON.map((row) => (
                <tr key={row.platform}>
                  <td style={{ fontWeight: 600 }}>{row.platform}</td>
                  <td className="num">{row.free}</td>
                  <td className="num">{row.pro}</td>
                  <td className="num">{row.business}</td>
                  <td className="num">{row.enterprise}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Honest limitations */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>What Statlas does not have</h2>
        <div className="card" style={{ padding: "var(--space-5)" }}>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {[
              "Live match data (coming in a future phase)",
              "Video playback (use Wyscout for match footage)",
              "Tactical formation AI (in development)",
              "Advanced computer vision (long-term roadmap)",
            ].map((item) => (
              <li key={item} style={{ padding: "var(--space-2) 0", borderBottom: "1px solid var(--color-divider)", fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                {item}
              </li>
            ))}
          </ul>
          <p style={{ marginTop: "var(--space-3)", fontSize: "var(--text-sm)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
            We believe in building what we know well, not everything.
          </p>
        </div>
      </section>

      {/* Testimonials */}
      <section style={{ marginTop: "var(--space-8)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>What switched users say</h2>
        <div className="grid">
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="card grid__span-4" style={{ padding: "var(--space-5)" }}>
              <p style={{ fontStyle: "italic", color: "var(--color-text-secondary)", marginBottom: "var(--space-2)", lineHeight: "var(--leading-relaxed)" }}>
                &ldquo;{t.quote}&rdquo;
              </p>
              <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>{t.name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ marginTop: "var(--space-8)", padding: "var(--space-8)", textAlign: "center", background: "var(--color-surface-raised)", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>See why 500+ teams switched to Statlas</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>Start with the free tier. No credit card required.</p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/register" className="button">Start free trial</Link>
          <Link href="/methodology" className="button button--secondary">View methodology</Link>
        </div>
      </section>
    </div>
  );
}
