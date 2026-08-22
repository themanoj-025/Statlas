import type { Metadata } from "next";
import Link from "next/link";
import SanitizedHTML from "@/components/SanitizedHTML";

const DOCS: Record<string, { title: string; category: string; content: string }> = {
  "getting-started": {
    title: "Getting Started",
    category: "Getting Started",
    content: `
<h2 id="welcome">Welcome to Statlas</h2>
<p>Statlas is a football analytics platform that publishes its methodology. Every metric on the site traces to a documented formula in the Metric Registry.</p>

<h2 id="what-you-can-do">What you can do with Statlas</h2>
<ul>
  <li><strong>Search for players</strong> using structured queries with up to 8 conditions</li>
  <li><strong>Compare players</strong> side-by-side on radar charts (up to 4 players)</li>
  <li><strong>Track trends</strong> with gap-aware weekly snapshot history</li>
  <li><strong>View shot and pass maps</strong> for competitions in StatsBomb Open Data coverage</li>
  <li><strong>Generate AI reports</strong> with every claim verified against real data</li>
  <li><strong>Organise shortlists</strong> with a six-stage status pipeline</li>
  <li><strong>Set up watchlists</strong> to monitor players for percentile movement</li>
</ul>

<h2 id="quick-start">5-minute quick start</h2>
<ol>
  <li>Go to <a href="/positions">Leaderboards</a> and pick a position group</li>
  <li>Click on a player to see their full profile with percentiles and the Statlas Index</li>
  <li>Use <a href="/compare">Compare</a> to overlay 2-4 players on a radar chart</li>
  <li>Check the <a href="/methodology">Methodology page</a> to understand how the numbers are calculated</li>
  <li>Create a free account to unlock saved searches and shortlists</li>
</ol>

<h2 id="next-steps">Next steps</h2>
<ul>
  <li><a href="/docs/understanding-radar-charts">How to read a radar chart</a></li>
  <li><a href="/docs/player-comparison">Player comparison guide</a></li>
  <li><a href="/docs/structured-search">Structured search tutorial</a></li>
  <li><a href="/docs/workspace-guide">Workspace and shortlists</a></li>
</ul>
    `,
  },
  "understanding-radar-charts": {
    title: "Understanding Radar Charts",
    category: "Features Guide",
    content: `
<h2 id="what-is-a-radar">What is a radar chart?</h2>
<p>A radar chart (also called a spider chart) displays multiple metrics as axes radiating from a central point. Each player's percentile rank is plotted on the corresponding axis, and the points are connected to form a polygon shape.</p>

<h2 id="reading-percentiles">Reading percentile values</h2>
<p>Each axis shows a percentile rank (0-100) within the player's position group and league tier. A percentile of 87 means the player exceeds 87% of qualifying peers in that metric.</p>
<p>Percentiles are not z-scores. Per-90 distributions are skewed and percentiles stay honest about that.</p>

<h2 id="comparison-mode">Comparison mode</h2>
<p>When comparing players, the radar overlays up to 4 polygons. Matched strengths (metrics where both players rank above the 70th percentile within 20 points) and key differences (gaps of 25+ percentile points) are explained below the chart.</p>

<h2 id="status-indicators">Status indicators</h2>
<p>Each axis shows one of four statuses:</p>
<ul>
  <li><strong>Qualified</strong> - percentile computed from sufficient data</li>
  <li><strong>Below floor</strong> - player has data but below the counter/minutes floor</li>
  <li><strong>No data</strong> - metric not available for this player</li>
  <li><strong>Unranked pool</strong> - too few peers in the group for a percentile</li>
</ul>

<h2 id="raw-vs-percentile">Raw values vs percentiles</h2>
<p>Use the toggle to switch between percentile ranks and raw per-90 values. Raw values show the actual statistic (e.g., 2.3 progressive passes per 90); percentiles show how that compares to peers.</p>
    `,
  },
  "player-comparison": {
    title: "Player Comparison Guide",
    category: "Features Guide",
    content: `
<h2 id="creating-comparison">Creating a comparison</h2>
<p>Go to <a href="/compare">/compare</a> and search for players by name. Select 2-4 players to overlay on a radar chart.</p>

<h2 id="understanding-results">Understanding results</h2>
<p>The comparison shows:</p>
<ul>
  <li><strong>Overlay radar</strong> - all players' percentiles on one chart</li>
  <li><strong>Matched strengths</strong> - metrics where both players are strong and aligned</li>
  <li><strong>Key differences</strong> - metrics with the largest percentile-point gap (25+ points)</li>
  <li><strong>Excluded metrics</strong> - metrics missing for either player, listed for transparency</li>
</ul>

<h2 id="similarity-score">Similarity score</h2>
<p>The similarity score uses cosine similarity over percentile vectors. A score of 0.95 means the players are very similar across all measured metrics.</p>

<h2 id="sharing">Sharing comparisons</h2>
<p>Every comparison generates a shareable permalink. Copy the URL to share with colleagues or embed the radar chart on external sites.</p>
    `,
  },
  "structured-search": {
    title: "Structured Search Guide",
    category: "Features Guide",
    content: `
<h2 id="building-queries">Building a query</h2>
<p>Go to <a href="/search">/search</a> and add conditions. Each condition has:</p>
<ul>
  <li><strong>Metric</strong> - the stat or attribute to filter on</li>
  <li><strong>Operator</strong> - equals, not equals, greater than, less than</li>
  <li><strong>Value</strong> - the threshold or exact value</li>
</ul>
<p>Up to 8 conditions are supported. All conditions use AND logic (every condition must match).</p>

<h2 id="condition-counts">Per-condition match counts</h2>
<p>As you add conditions, the search shows how many players match each individual condition and how many match all conditions combined. This helps you understand which conditions are most restrictive.</p>

<h2 id="saved-searches">Saved searches</h2>
<p>Save any search to re-run it later. Saved searches execute against current data on every run, so results always reflect the latest weekly refresh.</p>

<h2 id="presets">Search presets</h2>
<p>Curated presets for common scouting profiles are available. These provide a starting point that you can modify.</p>
    `,
  },
  "workspace-guide": {
    title: "Workspace & Shortlists Guide",
    category: "Features Guide",
    content: `
<h2 id="creating-shortlists">Creating shortlists</h2>
<p>Go to <a href="/workspace">/workspace</a> and create a new shortlist. Give it a name and optional description.</p>

<h2 id="adding-players">Adding players</h2>
<p>Add players to a shortlist from any player profile page or from search results. Each entry starts in the "discovered" status.</p>

<h2 id="status-pipeline">The status pipeline</h2>
<p>Move candidates through a six-stage pipeline:</p>
<ol>
  <li><strong>Discovered</strong> - player identified as a potential target</li>
  <li><strong>Monitoring</strong> - actively tracking the player</li>
  <li><strong>Scouted</strong> - detailed evaluation completed</li>
  <li><strong>Shortlisted</strong> - added to the formal shortlist</li>
  <li><strong>Reviewed</strong> - final evaluation by decision-makers</li>
  <li><strong>Signed</strong> or <strong>Rejected</strong> - terminal states</li>
</ol>

<h2 id="notes-tags">Notes and tags</h2>
<p>Add notes to any entry. Notes carry the author's name and timestamp. Tags help categorize entries (e.g., "summer target", "loan candidate").</p>

<h2 id="collaboration">Team collaboration</h2>
<p>On the Pro tier, invite team members to share a workspace. Everyone sees the same shortlists, notes, and status changes.</p>
    `,
  },
  "api-overview": {
    title: "API Overview",
    category: "API Reference",
    content: `
<h2 id="authentication">Authentication</h2>
<p>The API uses API key authentication. Generate a key from <a href="/account">account settings</a>. Include it in the <code>Authorization</code> header:</p>
<pre><code>Authorization: Bearer YOUR_API_KEY</code></pre>

<h2 id="rate-limits">Rate limits</h2>
<p>API Business tier: 1,000 requests per day. Rate limit headers are included in every response.</p>

<h2 id="response-format">Response format</h2>
<p>All responses are JSON. Errors follow a consistent structure:</p>
<pre><code>{
  "error": {
    "message": "Description of the error",
    "status": 400
  }
}</code></pre>

<h2 id="endpoints">Key endpoints</h2>
<ul>
  <li><code>GET /api/v1/meta</code> - Metric registry and position groups</li>
  <li><code>GET /api/v1/players/search?q=name</code> - Search for players</li>
  <li><code>GET /api/v1/players/by-slug/{slug}</code> - Player profile</li>
  <li><code>GET /api/v1/leaderboard</code> - Leaderboard entries</li>
  <li><code>GET /api/v1/coverage</code> - Data coverage matrix</li>
</ul>

<h2 id="full-documentation">Full documentation</h2>
<p>Interactive API documentation is available at <a href="/api-docs">/api-docs</a>, generated from the live OpenAPI specification.</p>
    `,
  },
  "faq": {
    title: "Frequently Asked Questions",
    category: "FAQ",
    content: `
<h2 id="data-questions">Data Questions</h2>

<h3 id="how-often">How often is data updated?</h3>
<p>Statistics refresh weekly on a scheduled cadence (currently Wednesday 03:00 UTC). Every stat block carries its snapshot date.</p>

<h3 id="data-sources">Where does the data come from?</h3>
<p>Per-90 statistics from FBref (Sports Reference), xG/xA for the Big-5 from Understat, event-level shot and pass data from StatsBomb Open Data where coverage exists.</p>

<h3 id="qualification">What is the qualification threshold?</h3>
<p>A player needs 900 league minutes in the current season before receiving a percentile rank or Index score. Below the threshold, per-90 rates are too noisy to rank fairly.</p>

<h2 id="account-questions">Account Questions</h2>

<h3 id="free-vs-pro">What is the difference between Free and Pro?</h3>
<p>Free includes full player pages, leaderboards (top 50), 3 comparisons per day, and the published methodology. Pro adds unlimited leaderboards, unlimited comparisons, 10 reports/month, team workspace, shot/pass maps, and API access.</p>

<h3 id="cancel">How do I cancel?</h3>
<p>From the billing portal in account settings. No email required. Pro access continues until the end of the paid period.</p>
    `,
  },
};

type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const doc = DOCS[slug];
  if (!doc) return { title: "Document not found" };
  return {
    title: doc.title,
    description: doc.content.replace(/<[^>]+>/g, "").slice(0, 160),
  };
}

export default async function DocPage({ params }: PageProps) {
  const { slug } = await params;
  const doc = DOCS[slug];

  if (!doc) {
    return (
      <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__title">Document not found</p>
          <p className="state-block__body">
            This documentation page does not exist. Check the URL or browse the docs index.
          </p>
          <div className="state-block__actions">
            <Link className="button button--sm" href="/docs">Back to docs</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/">Home</Link>
        <span className="breadcrumbs__sep" aria-hidden="true">/</span>
        <Link href="/docs">Docs</Link>
        <span className="breadcrumbs__sep" aria-hidden="true">/</span>
        <span aria-current="page">{doc.title}</span>
      </nav>

      <p className="kicker">{doc.category}</p>
      <h1 className="page__title">{doc.title}</h1>

      <SanitizedHTML html={doc.content} className="prose" />

      <div style={{ marginTop: "var(--space-6)" }}>
        <Link href="/docs" style={{ fontSize: "var(--text-sm)" }}>&larr; Back to documentation</Link>
      </div>
    </div>
  );
}

export function generateStaticParams() {
  return Object.keys(DOCS).map((slug) => ({ slug }));
}
