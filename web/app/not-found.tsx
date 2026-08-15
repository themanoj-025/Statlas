import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-sm)" }}>
      <div className="state-block state-block--sunken" role="status" style={{ marginTop: "var(--space-8)" }}>
        <p className="state-block__title">We couldn&rsquo;t find that page.</p>
        <p className="state-block__body">
          The URL may be misspelled, the player may be outside current data coverage, or the page
          may have moved. Try the search box above, or browse the{" "}
          <Link href="/positions">leaderboards</Link>.
        </p>
        <div className="state-block__actions">
          <Link className="button button--sm" href="/">
            Back to home
          </Link>
          <Link className="button button--secondary button--sm" href="/data-coverage">
            Check data coverage
          </Link>
        </div>
      </div>
    </div>
  );
}
