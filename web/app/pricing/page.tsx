import type { Metadata } from "next";
import { PricingClient } from "./PricingClient";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Free tier: full player pages, leaderboards (top 50), 3 comparisons per day. Pro: €7/month or €60/year — unlimited leaderboards, CSV export, PDF scout reports, embeds.",
  alternates: { canonical: "/pricing" },
};

export default function PricingPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Pricing</p>
      <h1 className="page__title">Pricing</h1>
      <p className="page__lede">
        The free tier is genuinely useful — full player pages and the published methodology are not
        gated. Pro adds volume and export for scouts and media.
      </p>
      <PricingClient />

      <h2 style={{ marginTop: "var(--space-6)", fontSize: "var(--text-xl)" }}>Questions worth asking</h2>
      <div className="faq">
        <details>
          <summary>How fresh is the data?</summary>
          <p>
            Statistics refresh on a weekly cadence (currently scheduled for Wednesday 03:00 UTC),
            and every stat block and leaderboard carries its snapshot date — &ldquo;Data as of
            YYYY-MM-DD&rdquo;. Nothing on Statlas is presented as live except the fixtures layer.
            See the <a href="/data-coverage">data coverage page</a> for exactly which sources,
            leagues, and seasons are available.
          </p>
        </details>
        <details>
          <summary>How do I cancel, and what happens to my access?</summary>
          <p>
            Cancellation is available from the billing portal in account settings — no email
            required. When you cancel, Pro access continues until the end of the paid period you
            already purchased (standard practice; you are never cut off mid-period). After the
            period ends, the account reverts to the Free tier.
          </p>
        </details>
        <details>
          <summary>What happens to my saved comparisons, permalinks, and exports after a downgrade?</summary>
          <p>
            Everything you created while on Pro stays yours: saved comparisons, shareable permalink
            URLs, embedded widgets, and exported reports continue to work and remain viewable.
            What reverts is the <em>volume</em> — leaderboards show the top 50 rows again, the
            comparison and trend windows return to free limits, and creating new embeds beyond the
            free allowance pauses until you upgrade again. We do not delete your work for not
            paying.
          </p>
        </details>
        <details>
          <summary>What happens if a payment fails?</summary>
          <p>
            You are not cut off immediately. Stripe retries the payment over several days, and
            during that window the account enters a grace period with a clear banner telling you
            exactly how to update your card and by when, so Pro access continues uninterrupted.
            Only if the payment is still not collected after the retries does the subscription end.
          </p>
        </details>
        <details>
          <summary>Why is there a free tier at all?</summary>
          <p>
            The free tier is the proof of the product: the full methodology, real player pages,
            and real percentiles are not gated, so anyone can verify the numbers before paying.
            Free users are limited on volume (top 50 leaderboard rows, 3 comparisons per day, a
            5-snapshot trend window, 10 assistant queries per month) — not on data integrity.
          </p>
        </details>
        <details>
          <summary>Is there an API or a business tier?</summary>
          <p>
            Yes — API Business (€49/month) adds key-based access to the public API with
            documented rate limits, for media, agents, and smaller clubs. The API is versioned,
            documented from the live spec at <a href="/api-docs">/api-docs</a>, and API keys are
            managed from account settings with rotation and revocation.
          </p>
        </details>
        <details>
          <summary>I found a wrong number. What do I do?</summary>
          <p>
            Tell us. Data-accuracy reports go to <a href="mailto:data@statlas.com">data@statlas.com</a>
            and are read first, because a number that does not match the published methodology is
            a bug we want to find before our users do.
          </p>
        </details>
      </div>
    </div>
  );
}
