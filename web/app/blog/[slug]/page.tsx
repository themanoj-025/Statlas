import type { Metadata } from "next";
import Link from "next/link";

// Blog posts are currently static content (no CMS). Each slug maps to a
// hardcoded post. When a CMS is added, this page should fetch from it.

const POSTS: Record<string, { title: string; date: string; author: string; readTime: string; category: string; content: string; headings: { id: string; text: string }[] }> = {
  "statlas-index-explained": {
    title: "The Statlas Index: A Weighted Composite Score, Fully Published",
    date: "2026-07-28",
    author: "Statlas Team",
    readTime: "12 min",
    category: "Methodology",
    headings: [
      { id: "what-it-measures", text: "What the Index measures" },
      { id: "the-weights", text: "The weights" },
      { id: "the-formula", text: "The formula" },
      { id: "minimum-requirements", text: "Minimum requirements" },
      { id: "what-it-does-not-do", text: "What the Index does not do" },
    ],
    content: `
<h2 id="what-it-measures">What the Index measures</h2>
<p>The Statlas Index answers one question: how productive is a player's per-90 output relative to their positional peers in comparable leagues this season? It is a weighted average of percentile ranks.</p>

<h2 id="the-weights">The weights</h2>
<p>Weights depend on position and every row sums to 1.00. A striker's index leans on goals and xG; a centre-back's leans on defensive actions and build-up.</p>

<h2 id="the-formula">The formula</h2>
<blockquote>Index = Σ (w_i / W_present) × p_i</blockquote>
<p>Where w_i is the position weight for metric i, W_present is the sum of weights for all metrics with data, and p_i is the percentile rank for metric i.</p>

<h2 id="minimum-requirements">Minimum requirements</h2>
<p>Outfield players need 8+ of 12 metrics. Goalkeepers need 3+ of 4 metrics. Below these thresholds, the Index is not computed.</p>

<h2 id="what-it-does-not-do">What the Index does not do</h2>
<ul>
  <li>Does not account for role within a system</li>
  <li>Does not weight quality of opposition or game state</li>
  <li>Is not a prediction of future performance or transfer value</li>
  <li>Is computed from per-90 output, not minutes-weighted contribution</li>
</ul>
    `,
  },
  "search-builder-guide": {
    title: "Finding Players with Structured Search",
    date: "2026-07-20",
    author: "Statlas Team",
    readTime: "7 min",
    category: "Feature Guides",
    headings: [
      { id: "building-a-query", text: "Building a query" },
      { id: "understanding-results", text: "Understanding results" },
      { id: "saved-searches", text: "Saved searches" },
    ],
    content: `
<h2 id="building-a-query">Building a query</h2>
<p>Go to <a href="/search">/search</a> and add conditions. Each condition specifies a metric, an operator, and a value. Up to 8 conditions are supported, all using AND logic.</p>

<h2 id="understanding-results">Understanding results</h2>
<p>Every result entry carries condition_values showing the real stored values behind each condition. Per-condition match counts help you understand which conditions are most restrictive.</p>

<h2 id="saved-searches">Saved searches</h2>
<p>Save any search to re-run it later. Saved searches execute against current data on every run.</p>
    `,
  },
  "how-we-calculate-percentiles": {
    title: "Methodology Deep Dive: How We Calculate Percentiles",
    date: "2026-08-15",
    author: "Statlas Team",
    readTime: "8 min",
    category: "Methodology",
    headings: [
      { id: "the-formula", text: "The formula" },
      { id: "position-groups", text: "Position groups" },
      { id: "league-tiers", text: "League tiers" },
      { id: "qualifying-threshold", text: "The qualifying threshold" },
      { id: "worked-example", text: "Worked example" },
    ],
    content: `
<p>Every per-90 statistic on Statlas is converted to a percentile rank within the player's position group and league tier. The formula is the standard fractional-rank percentile:</p>

<blockquote>P = (B + 0.5 × E) / N × 100</blockquote>

<p>Where B is the number of qualifying peers below the player's value, E the number exactly equal, and N the total qualifying players in the group. Ties split the difference.</p>

<h2 id="the-formula">The formula</h2>
<p>Percentiles, not z-scores. Per-90 distributions are skewed and percentiles stay honest about that. A percentile of 87 means "exceeds 87% of qualifying peers in this group."</p>

<h2 id="position-groups">Position groups</h2>
<p>Players are compared within their position group: strikers against strikers, midfielders against midfielders, and so on. The eight position groups are defined in the Metric Registry.</p>

<h2 id="league-tiers">League tiers</h2>
<p>Percentiles are computed within a league tier, not per league and not globally. Tier 1 covers the Big-5 European leagues; Tier 2 covers strong second-tier leagues; Tier 3 covers second divisions of the Big-5.</p>

<h2 id="qualifying-threshold">The qualifying threshold</h2>
<p>A player receives a percentile rank after 900 league minutes in the current season. Below that, per-90 rates are too noisy to rank fairly.</p>

<h2 id="worked-example">Worked example</h2>
<p>See the <a href="/methodology">Methodology page</a> for a full worked example with real player numbers, including the weighted Statlas Index calculation.</p>
    `,
  },
  "honest-trend-charts": {
    title: "The Truth About Trend Charts: Why We Draw Gaps as Gaps",
    date: "2026-08-10",
    author: "Statlas Team",
    readTime: "6 min",
    category: "Methodology",
    headings: [
      { id: "what-are-gaps", text: "What are gaps?" },
      { id: "why-not-interpolate", text: "Why not interpolate?" },
      { id: "how-statlas-handles-them", text: "How Statlas handles them" },
    ],
    content: `
<h2 id="what-are-gaps">What are gaps?</h2>
<p>A gap in a trend chart means a snapshot was not available for that period. This happens when a player was injured, transferred mid-season, or when a data source failed to produce a snapshot.</p>

<h2 id="why-not-interpolate">Why not interpolate?</h2>
<p>Interpolation creates a number that does not exist in the data. If a player missed three weeks, the stat for that period is unknown — not "somewhere between the previous and next value." Drawing a gap is honest; interpolating is fabrication.</p>

<h2 id="how-statlas-handles-them">How Statlas handles them</h2>
<p>Gaps are drawn as dashed breaks in the trend line. The chart notes the reason for the gap when it is known (injury, transfer, data source issue). Anomaly-flagged snapshots are marked with a warning indicator.</p>
    `,
  },
  "ai-reports-verification": {
    title: "AI in Scouting: What It Can (and Cannot) Do",
    date: "2026-08-05",
    author: "Statlas Team",
    readTime: "10 min",
    category: "Product Updates",
    headings: [
      { id: "the-verification-gate", text: "The verification gate" },
      { id: "what-gets-checked", text: "What gets checked" },
      { id: "confidence-scoring", text: "Confidence scoring" },
      { id: "limitations", text: "Limitations" },
    ],
    content: `
<h2 id="the-verification-gate">The verification gate</h2>
<p>Every AI-generated claim in a scouting report is verified against the data before the report is finalised. A fabricated statistic fails the gate and the report is retried once with the mismatch fed back. A second failure stores the report as "needs review" — never silently shipped.</p>

<h2 id="what-gets-checked">What gets checked</h2>
<p>Every narrative number, every metric name, and every comparable player is cross-referenced against the verification corpus — the real data the report was built from. If the AI says a player is in the "90th percentile for progressive passes," that number must match the published percentile snapshot.</p>

<h2 id="confidence-scoring">Confidence scoring</h2>
<p>Confidence is computed deterministically from sample size, data completeness, and recency. A player with 2,000+ minutes and 95% metric coverage scores higher than one with 1,000 minutes and 70% coverage.</p>

<h2 id="limitations">Limitations</h2>
<p>AI reports are a starting point for human evaluation, not a replacement for it. The report does not account for context that is not in the data: injuries, tactical role changes, dressing room dynamics, or opposition quality.</p>
    `,
  },
};

type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = POSTS[slug];
  if (!post) return { title: "Article not found" };
  return {
    title: post.title,
    description: post.content.replace(/<[^>]+>/g, "").slice(0, 160),
    openGraph: { title: post.title, type: "article", publishedTime: post.date },
  };
}

export default async function BlogPostPage({ params }: PageProps) {
  const { slug } = await params;
  const post = POSTS[slug];

  if (!post) {
    return (
      <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Article not found</p>
          <p className="state-block__body">
            The article you are looking for does not exist or has been moved.
          </p>
          <div className="state-block__actions">
            <Link className="button button--sm" href="/blog">Back to blog</Link>
          </div>
        </div>
      </div>
    );
  }

  const formattedDate = new Date(post.date).toLocaleDateString("en-GB", {
    day: "numeric", month: "long", year: "numeric",
  });

  return (
    <article className="container page" style={{ maxWidth: "var(--container-md)" }}>
      {/* Header */}
      <header style={{ marginBottom: "var(--space-6)" }}>
        <span className="chip chip--accent" style={{ marginBottom: "var(--space-2)" }}>{post.category}</span>
        <h1 style={{ fontSize: "var(--text-3xl)", marginBottom: "var(--space-3)" }}>{post.title}</h1>
        <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          <span>{post.author}</span>
          <span>{formattedDate}</span>
          <span>{post.readTime} read</span>
        </div>
      </header>

      {/* Table of Contents */}
      <nav className="card" style={{ padding: "var(--space-4)", marginBottom: "var(--space-6)" }}>
        <p style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--space-2)", marginTop: 0 }}>Table of contents</p>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {post.headings.map((h) => (
            <li key={h.id} style={{ marginBottom: "var(--space-1)" }}>
              <a href={`#${h.id}`} style={{ fontSize: "var(--text-sm)" }}>{h.text}</a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Content */}
      <div className="prose" dangerouslySetInnerHTML={{ __html: post.content }} />

      {/* Share */}
      <section className="card" style={{ padding: "var(--space-4)", marginTop: "var(--space-6)" }}>
        <p style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: "var(--space-2)", marginTop: 0 }}>Share this article</p>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <a className="button button--sm button--secondary" href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(post.title)}&url=${encodeURIComponent(`https://statlas.com/blog/${slug}`)}`} target="_blank" rel="noopener noreferrer">Twitter</a>
          <a className="button button--sm button--secondary" href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(`https://statlas.com/blog/${slug}`)}`} target="_blank" rel="noopener noreferrer">LinkedIn</a>
        </div>
      </section>

      {/* Back to blog */}
      <div style={{ marginTop: "var(--space-6)" }}>
        <Link href="/blog" style={{ fontSize: "var(--text-sm)" }}>&larr; Back to all articles</Link>
      </div>
    </article>
  );
}
