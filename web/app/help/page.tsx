import type { Metadata } from "next";
import Link from "next/link";
import { BarChart3, CreditCard, Database, Settings, Shield, HelpCircle } from "lucide-react";

export const metadata: Metadata = {
  title: "Help & FAQ",
  description:
    "How percentiles and the Statlas Index are calculated, why a player may be missing, how billing and cancellation work, and how to report a data error.",
  alternates: { canonical: "/help" },
};

const CATEGORIES = [
  {
    icon: Database,
    title: "Data & Methodology",
    questions: [
      {
        q: "How are percentiles calculated?",
        a: "Every per-90 statistic is converted to a percentile rank within the player\u2019s position group and league tier, using the standard fractional-rank formula: P = (B + 0.5 \u00d7 E) / N \u00d7 100. The full formula, position weights, and a worked example with real numbers are on the Methodology page.",
      },
      {
        q: "Why is a player missing, or showing \u201cpending qualification\u201d?",
        a: "Three reasons: (1) below the 900-minute minutes threshold, (2) outside current data coverage, or (3) a scrape failed or is pending review. The page tells you which one applies.",
      },
      {
        q: "Why is a player\u2019s percentile different across pages or over time?",
        a: "Percentiles are computed within the latest published snapshot. Every stat block shows its snapshot date, and percentiles are recomputed after each weekly refresh as the qualifying cohort changes. If two pages disagree for the same snapshot date, that is a bug.",
      },
      {
        q: "How current is the data?",
        a: "Statistics refresh weekly (currently scheduled Wednesday 03:00 UTC). Nothing on the site is presented as live except the fixtures layer. Every player page, leaderboard, and stat block carries its snapshot date.",
      },
      {
        q: "Why is a stat shown as 0 instead of \u201cno data\u201d?",
        a: "Each metric has a documented null-vs-zero policy. Goals per 90 is 0 for a player who has not scored; a metric with no value shows \u201cN/A\u201d. The policy is defined per metric in the registry.",
      },
      {
        q: "How do you handle transfers mid-season?",
        a: "A player\u2019s statistics are keyed to the team in the snapshot that recorded them. After a transfer, new snapshots reflect the new club. The roster on a team page is honest about mid-season placements.",
      },
    ],
  },
  {
    icon: BarChart3,
    title: "Features",
    questions: [
      {
        q: "How do I compare players?",
        a: "Use the Compare page to overlay up to 4 players on a radar chart. Every axis is a named metric with a published definition. Matched strengths and key differences are explained from the percentile data.",
      },
      {
        q: "How do trend charts work?",
        a: "Trend charts show a rolling window of weekly snapshot percentiles. Gaps are drawn as dashed breaks, never interpolated. Anomaly-flagged snapshots are marked with a warning indicator.",
      },
      {
        q: "What do shot and pass maps show?",
        a: "Event-level shot and pass data from StatsBomb Open Data, covering specific released competitions. Coverage is gated \u2014 if the data does not exist, the page says so explicitly.",
      },
      {
        q: "How do AI scouting reports work?",
        a: "Every AI-generated claim is verified against the data before a report is finalised. A fabricated statistic fails the verification gate and is retried. The evidence appendix makes each figure traceable to its source.",
      },
    ],
  },
  {
    icon: CreditCard,
    title: "Billing & Account",
    questions: [
      {
        q: "How does billing and cancellation work?",
        a: "Billing is handled by Stripe Checkout. You can cancel from the billing portal at any time. Pro access continues until the end of the paid period, then the account reverts to Free.",
      },
      {
        q: "What happens to my saved work if I downgrade?",
        a: "Everything you created while on Pro stays yours: saved comparisons, permalinks, embeds, and exports. Only the volume limits revert to free-tier levels.",
      },
      {
        q: "What happens if a payment fails?",
        a: "Stripe retries the payment over several days. During that window the account enters a grace period with clear on-site messaging. Only if the payment is still not collected after retries does the subscription end.",
      },
      {
        q: "Why is there a free tier?",
        a: "The free tier is the proof of the product. The full methodology, real player pages, and real percentiles are not gated. Free users are limited on volume, not on data integrity.",
      },
    ],
  },
  {
    icon: Settings,
    title: "Workspace & Search",
    questions: [
      {
        q: "How does the workspace pipeline work?",
        a: "Shortlists follow a six-stage pipeline: discovered, monitoring, scouted, shortlisted, reviewed, and signed/rejected. Every status change carries who, when, and why.",
      },
      {
        q: "How does structured search work?",
        a: "Multi-condition search with AND logic across position, age, league, and metrics. Up to 8 conditions per query. Saved searches re-execute against current data on every run.",
      },
      {
        q: "How does the watchlist work?",
        a: "Follow players and teams to receive alerts on percentile movement, club changes, and data-quality events. Alerts carry real data, not templated messages.",
      },
    ],
  },
  {
    icon: Shield,
    title: "Privacy & Security",
    questions: [
      {
        q: "How do you handle player data under GDPR?",
        a: "Player performance statistics are processed under legitimate interests. We document a retention policy, implement data-subject request paths, and publish a privacy policy that matches our actual practices.",
      },
      {
        q: "How do I report a data error?",
        a: "Every player and team page has a \u201cReport a data error\u201d link. It opens a pre-filled email to data@statlas.com naming the page you were on. Data-accuracy reports are read first.",
      },
    ],
  },
  {
    icon: HelpCircle,
    title: "Technical",
    questions: [
      {
        q: "Can I use the API?",
        a: "Yes \u2014 the public API is available on the API Business tier. It is versioned, rate limited, and documented from the live spec at /api-docs. API keys are managed from account settings.",
      },
      {
        q: "How do I embed charts on my site?",
        a: "Embeddable radar and trend widgets are available as HTML iframes. Each embed carries Statlas attribution and links back to the methodology.",
      },
    ],
  },
];

export default function HelpPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Help</p>
      <h1 className="page__title">Help &amp; FAQ</h1>
      <p className="page__lede">
        Straight answers about the data, the methodology, and your account. If your question is
        not here, write to{" "}
        <a href="mailto:data@statlas.com">data@statlas.com</a>.
      </p>

      {/* Category index */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-6)" }}>
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          return (
            <a
              key={cat.title}
              href={`#${cat.title.toLowerCase().replace(/[& ]/g, "-")}`}
              className="chip"
              style={{ cursor: "pointer" }}
            >
              <Icon size={12} aria-hidden="true" /> {cat.title}
            </a>
          );
        })}
      </div>

      {/* Categories with questions */}
      {CATEGORIES.map((cat) => {
        const Icon = cat.icon;
        return (
          <section key={cat.title} id={cat.title.toLowerCase().replace(/[& ]/g, "-")} style={{ marginBottom: "var(--space-6)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
              <Icon size={18} color="var(--color-primary)" aria-hidden="true" />
              <h2 style={{ fontSize: "var(--text-xl)", margin: 0 }}>{cat.title}</h2>
            </div>
            <div className="faq">
              {cat.questions.map((qa) => (
                <details key={qa.q}>
                  <summary>{qa.q}</summary>
                  <p>{qa.a}</p>
                </details>
              ))}
            </div>
          </section>
        );
      })}

      {/* Contact */}
      <section
        style={{
          marginTop: "var(--space-6)",
          padding: "var(--space-5)",
          textAlign: "center",
          background: "var(--color-surface-raised)",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--color-border)",
        }}
      >
        <h2 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>
          Still have questions?
        </h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-3)", fontSize: "var(--text-sm)" }}>
          Write to <a href="mailto:data@statlas.com">data@statlas.com</a> and we will respond
          within 24 hours.
        </p>
        <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
          <Link href="/contact" className="button button--sm">Contact support</Link>
          <Link href="/docs" className="button button--secondary button--sm">Documentation</Link>
        </div>
      </section>
    </div>
  );
}
