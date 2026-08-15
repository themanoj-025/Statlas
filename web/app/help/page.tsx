import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Help & FAQ",
  description:
    "How percentiles and the Statlas Index are calculated, why a player may be missing, how billing and cancellation work, and how to report a data error.",
  alternates: { canonical: "/help" },
};

export default function HelpPage() {
  return (
    <div className="container page" style={{ maxWidth: "var(--container-md)" }}>
      <p className="kicker">Help</p>
      <h1 className="page__title">Help &amp; FAQ</h1>
      <p className="page__lede">
        Straight answers about the data, the methodology, and your account. If your question is
        not here, write to <a href="mailto:data@statlas.com">data@statlas.com</a>.
      </p>

      <div className="faq">
        <details open>
          <summary>How are percentiles calculated?</summary>
          <p>
            Every per-90 statistic is converted to a percentile rank within the player&rsquo;s
            position group and league tier, using the standard fractional-rank formula. The
            percentile is labelled with its tier — a Tier 1 percentile is not comparable to a Tier
            3 percentile. The full formula, position weights, and a worked example with real
            numbers are on the <a href="/methodology">Methodology page</a>.
          </p>
        </details>
        <details>
          <summary>Why is a player missing, or showing &ldquo;pending qualification&rdquo;?</summary>
          <p>
            Three reasons, and the page tells you which one applies:
          </p>
          <ul>
            <li>
              <strong>Below the minutes threshold.</strong> A player needs{" "}
              <strong>900 league minutes</strong> this season before they receive a percentile
              rank or an Index score — below that, per-90 rates are too noisy to rank fairly. The
              profile says exactly how many more minutes are needed.
            </li>
            <li>
              <strong>Outside current data coverage.</strong> Statlas currently covers a specific
              set of leagues and seasons. If a player plays in a league outside that coverage,
              they do not appear. The <a href="/data-coverage">data coverage page</a> lists
              exactly what is covered — Statlas never implies coverage it does not have.
            </li>
            <li>
              <strong>A scrape failed or is pending review.</strong> New data is published only
              after the weekly refresh&rsquo;s anomaly check passes. A player whose latest values
              were flagged is held back rather than shown with unverified numbers.
            </li>
          </ul>
        </details>
        <details>
          <summary>Why is a player&rsquo;s percentile different across pages or over time?</summary>
          <p>
            Percentiles are computed within the latest published snapshot. Every stat block shows
            its snapshot date (&ldquo;Data as of YYYY-MM-DD&rdquo;), and percentiles are
            recomputed after each weekly refresh as the qualifying cohort changes. If two pages
            disagree <em>for the same snapshot date</em>, that is a bug — report it.
          </p>
        </details>
        <details>
          <summary>How current is the data?</summary>
          <p>
            Statistics refresh weekly (currently scheduled Wednesday 03:00 UTC). Nothing on the
            site is presented as live except the fixtures layer. Every player page, leaderboard,
            and stat block carries its snapshot date so you never have to guess.
          </p>
        </details>
        <details>
          <summary>How does billing and cancellation work?</summary>
          <p>
            Billing is handled by Stripe Checkout — card details never touch Statlas servers.
            You can cancel from the billing portal in account settings at any time; Pro access
            continues until the end of the paid period, then the account reverts to Free.
            Payment failures trigger a grace period with clear on-site messaging instead of an
            immediate cutoff. More on the <a href="/pricing">pricing page</a>.
          </p>
        </details>
        <details>
          <summary>What happens to my saved work if I downgrade?</summary>
          <p>
            Everything you created while on Pro — saved comparisons, permalinks, embeds, and
            exports — remains yours and keeps working. Only the volume limits revert to free-tier
            levels. Statlas does not delete your work for not paying.
          </p>
        </details>
        <details>
          <summary>How do I report a data error?</summary>
          <p>
            Every player and team page has a <strong>&ldquo;Report a data error&rdquo;</strong>{" "}
            link. It opens a pre-filled email to <a href="mailto:data@statlas.com">data@statlas.com</a>{" "}
            naming the page you were on, so the fastest possible fix starts with the right
            context. Data-accuracy reports are read first — a wrong number is the most serious
            bug Statlas can have. If your report is about a number that does not match the
            published methodology, say so in the subject line.
          </p>
        </details>
        <details>
          <summary>Can I use the API?</summary>
          <p>
            Yes — the public API is available on the API Business tier. It is versioned, rate
            limited, and documented from the live spec at <a href="/api-docs">/api-docs</a>.
            API keys are generated, rotated, and revoked from account settings; the full key is
            shown only once at creation.
          </p>
        </details>
        <details>
          <summary>Why is a stat shown as 0 instead of &ldquo;no data&rdquo;?</summary>
          <p>
            Each metric has a documented null-vs-zero policy. For example, goals per 90 is shown
            as 0 for a player who genuinely has not scored; a metric with no value in the latest
            snapshot shows &ldquo;N/A&rdquo;. The policy is defined per metric in the registry and
            rendered consistently across the site.
          </p>
        </details>
      </div>
    </div>
  );
}
