import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About Statlas — an analytics platform that shows its work",
  description:
    "Why Statlas exists: football analytics that publishes its formulas instead of hiding them behind a black box. What the product is, what it is not, and how it is built.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">About</p>
      <h1 className="page__title">Statlas shows its work</h1>
      <div className="prose">
        <p>
          Statlas is a football data platform for people who already read the sport closely:
          independent scouts, analysts, agents, media, and serious fans. It answers the question{" "}
          <em>&ldquo;how productive is this player, relative to their positional peers in
          comparable leagues?&rdquo;</em> with per-90 statistics, percentile ranks, a published
          composite index, trend history, and — where the data exists — shot and pass maps.
        </p>

        <h2>Why it exists</h2>
        <p>
          Most analytics tools treat their composite scores as a trade secret. You see a number,
          you are told to trust it, and you cannot check how it was produced. That is a strange
          arrangement for an audience whose entire job is verifying claims about footballers.
        </p>
        <p>
          Statlas is built the other way around. The Statlas Index formula, its input metrics, its
          position weights, its qualifying threshold, and its known limitations are all published
          on the <a href="/methodology">Methodology page</a>, generated from the same registry the
          code reads. Every stat block carries its snapshot date. Coverage claims are enforced
          against a machine-readable coverage matrix, so the site can never imply it has data it
          does not have. If a number on the site does not match the published formula, that is a
          bug — and we want to hear about it.
        </p>

        <h2>What Statlas is not</h2>
        <ul>
          <li>not a prediction tool — the Index measures this season&rsquo;s per-90 output, not future performance, transfer value, or injury risk;</li>
          <li>not a live data service — statistics refresh on a weekly cadence and are labelled with their snapshot date; only the fixtures layer is ever called &ldquo;live&rdquo;;</li>
          <li>not a universal event-data provider — shot and pass maps render only for the competitions in StatsBomb Open Data coverage, and say so explicitly where they are absent;</li>
          <li>not a black box — every derived metric on the site has a registry entry and a published definition.</li>
        </ul>

        <h2>Who builds it</h2>
        <p>
          One person. Statlas is currently a solo project — there is no team to imply and no
          startup narrative to perform. It is built and maintained by a single developer who
          wanted a scouting tool that could survive being checked, and decided to make the
          checking part of the product.
        </p>

        <h2>How it is built</h2>
        <p>
          Server-rendered Next.js pages over a versioned FastAPI backend, PostgreSQL for
          structured data, and a modular data-source layer that can swap scraped feeds for a
          licensed feed as revenue justifies it. The engineering standards — tested parsers,
          append-only snapshots, an anomaly gate before anything is published, automated
          accessibility and performance checks in CI — are documented in the project&rsquo;s
          public engineering docs, because &ldquo;we take data integrity seriously&rdquo; is a
          claim best made by showing the checks, not by asserting them.
        </p>

        <h2>Contact</h2>
        <p>
          Found an error in the data? A mismatch between the methodology and a number on the
          site? Something that should work but does not? <a href="mailto:data@statlas.com">Write
          to data@statlas.com</a> — data-accuracy reports are read first.
        </p>
      </div>
    </div>
  );
}
