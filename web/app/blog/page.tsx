import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Insights on football data, scouting methodology, and analytics. Deep dives into how Statlas calculates its metrics.",
  alternates: { canonical: "/blog" },
};

const CATEGORIES = [
  { name: "Methodology", count: 15 },
  { name: "Case Studies", count: 8 },
  { name: "Feature Guides", count: 22 },
  { name: "Analytics", count: 12 },
  { name: "Product Updates", count: 18 },
];

const FEATURED_ARTICLES = [
  {
    slug: "how-we-calculate-percentiles",
    title: "Methodology Deep Dive: How We Calculate Percentiles",
    excerpt:
      "The fractional-rank formula, position groups, league tiers, and the 900-minute qualifying threshold — explained with real numbers.",
    author: "Statlas Team",
    date: "2026-08-15",
    readTime: "8 min",
    category: "Methodology",
  },
  {
    slug: "honest-trend-charts",
    title: "The Truth About Trend Charts: Why We Draw Gaps as Gaps",
    excerpt:
      "Most analytics tools interpolate missing data. Statlas does not. Here is why gap-aware trends are more honest.",
    author: "Statlas Team",
    date: "2026-08-10",
    readTime: "6 min",
    category: "Methodology",
  },
  {
    slug: "ai-reports-verification",
    title: "AI in Scouting: What It Can (and Cannot) Do",
    excerpt:
      "Every AI-generated claim on Statlas is verified against real data before the report is finalised. Here is how the verification gate works.",
    author: "Statlas Team",
    date: "2026-08-05",
    readTime: "10 min",
    category: "Product Updates",
  },
];

const ALL_ARTICLES = [
  ...FEATURED_ARTICLES,
  { slug: "statlas-index-explained", title: "The Statlas Index: A Weighted Composite Score, Fully Published", excerpt: "How the 12 outfield metrics are combined with position-specific weights.", author: "Statlas Team", date: "2026-07-28", readTime: "12 min", category: "Methodology" },
  { slug: "search-builder-guide", title: "Finding Players with Structured Search", excerpt: "A walkthrough of the multi-condition search builder with practical examples.", author: "Statlas Team", date: "2026-07-20", readTime: "7 min", category: "Feature Guides" },
  { slug: "workspace-pipeline", title: "Your Scouting Pipeline, Digitised", excerpt: "How the six-stage status pipeline works and why it matters for team collaboration.", author: "Statlas Team", date: "2026-07-15", readTime: "5 min", category: "Feature Guides" },
  { slug: "shot-maps-statsbomb", title: "Shot Maps: What StatsBomb Open Data Covers (and What It Does Not)", excerpt: "Coverage boundaries, attribution requirements, and how to read an event map.", author: "Statlas Team", date: "2026-07-10", readTime: "9 min", category: "Analytics" },
  { slug: "tier-structure-explained", title: "Why Percentiles Use League Tiers, Not Individual Leagues", excerpt: "The tier structure, cross-league comparability, and why a Tier 1 percentile is not the same as a Tier 3 percentile.", author: "Statlas Team", date: "2026-07-05", readTime: "6 min", category: "Methodology" },
  { slug: "data-coverage-matrix", title: "The Data Coverage Matrix: How We Enforce Honesty", excerpt: "A machine-readable file that prevents the site from claiming coverage it does not have.", author: "Statlas Team", date: "2026-06-28", readTime: "4 min", category: "Product Updates" },
];

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export default function BlogPage() {
  return (
    <div className="container page">
      <p className="kicker">Blog</p>
      <h1 className="page__title">Statlas analytics blog</h1>
      <p className="page__lede">
        Insights on football data, scouting methodology, and analytics. Every article
        links to the methodology it references.
      </p>

      {/* Categories */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-6)" }}>
        {CATEGORIES.map((cat) => (
          <span key={cat.name} className="chip">
            {cat.name} ({cat.count})
          </span>
        ))}
      </div>

      {/* Featured articles */}
      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>Featured</h2>
      <div className="grid" style={{ marginBottom: "var(--space-8)" }}>
        {FEATURED_ARTICLES.map((article) => (
          <Link key={article.slug} href={`/blog/${article.slug}`} className="card grid__span-4" style={{ textDecoration: "none", color: "var(--color-text-primary)" }}>
            <span className="chip chip--accent" style={{ marginBottom: "var(--space-2)" }}>{article.category}</span>
            <h3 style={{ fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>{article.title}</h3>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginBottom: "var(--space-3)" }}>{article.excerpt}</p>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", display: "flex", gap: "var(--space-3)" }}>
              <span>{article.author}</span>
              <span>{formatDate(article.date)}</span>
              <span>{article.readTime}</span>
            </div>
          </Link>
        ))}
      </div>

      {/* All articles */}
      <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-4)" }}>All articles</h2>
      <div style={{ display: "grid", gap: "var(--space-3)" }}>
        {ALL_ARTICLES.map((article) => (
          <Link key={article.slug} href={`/blog/${article.slug}`} className="card" style={{ textDecoration: "none", color: "var(--color-text-primary)", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-4)" }}>
            <div>
              <span className="chip" style={{ marginRight: "var(--space-2)" }}>{article.category}</span>
              <h3 style={{ fontSize: "var(--text-base)", marginTop: "var(--space-2)", marginBottom: "var(--space-1)" }}>{article.title}</h3>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", margin: 0 }}>{article.excerpt}</p>
            </div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", whiteSpace: "nowrap", marginLeft: "var(--space-4)" }}>
              {formatDate(article.date)}
            </div>
          </Link>
        ))}
      </div>

      {/* Newsletter signup */}
      <section style={{ marginTop: "var(--space-8)", padding: "var(--space-6)", textAlign: "center", background: "var(--color-surface-raised)", borderRadius: "var(--radius-xl)", border: "1px solid var(--color-border)" }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: "var(--space-2)" }}>Stay updated</h2>
        <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--space-4)" }}>
          Weekly insights on football analytics, methodology updates, and new features.
        </p>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Newsletter coming soon. Check back for updates.
        </p>
      </section>
    </div>
  );
}
