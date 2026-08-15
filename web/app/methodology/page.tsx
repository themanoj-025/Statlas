import type { Metadata } from "next";
import { api } from "@/lib/api";

export const metadata: Metadata = {
  title: "Methodology — the Statlas Index, fully published",
  description:
    "The Statlas Index formula in full: input metrics, position weights, fractional-rank percentiles, the 900-minute qualifying threshold, and what the index deliberately does not measure.",
  alternates: { canonical: "/methodology" },
};

export default async function MethodologyPage() {
  const meta = await api.meta();
  const outfield = meta.position_groups.filter((g) => g.code !== "GK");
  const gk = meta.position_groups.find((g) => g.code === "GK");

  return (
    <div className="container page">
      <p className="kicker">Methodology</p>
      <h1 className="page__title">The Statlas Index — how it works</h1>
      <div className="prose">
        <p>
          <strong>Statlas publishes its formula.</strong> Most analytics tools treat their composite
          score as a trade secret. We do not. Every number on this page traces to a documented
          calculation, and the calculation is the one the site uses. If you find a discrepancy
          between this page and a number you see, that is a bug — tell us at data@statlas.com.
        </p>

        <h2>What the Index measures</h2>
        <p>
          The Statlas Index answers one question: <em>how productive is a player&rsquo;s per-90
          output relative to their positional peers in comparable leagues this season?</em> It is a
          weighted average of percentile ranks. Each underlying statistic is converted into a
          percentile within the player&rsquo;s position group and league tier, and those percentiles
          are combined with position-specific weights. Scores run 0–100.
        </p>

        <h2>The inputs</h2>
        <p>
          {Object.values(meta.metrics).length} registry metrics, all sourced from FBref and
          Understat. Each entry below is the registry&rsquo;s definition — the same entry the code
          reads (methodology-as-code; the page cannot drift from the numbers).
        </p>
        <div className="table-wrap" role="region" aria-label="Index input metrics" tabIndex={0}>
          <table className="table" style={{ minWidth: 560 }}>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col">Unit</th>
                <th scope="col">Direction</th>
                <th scope="col">Definition</th>
              </tr>
            </thead>
            <tbody>
              {Object.values(meta.metrics).map((metric) => (
                <tr key={metric.id}>
                  <td><strong>{metric.name}</strong></td>
                  <td>{metric.unit}</td>
                  <td>{metric.lower_is_better ? "lower is better" : "higher is better"}</td>
                  <td>{metric.definition}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2>The weights</h2>
        <p>
          Weights depend on position and every row sums to 1.00. A striker&rsquo;s index leans on
          goals and xG; a centre-back&rsquo;s leans on defensive actions and build-up.
        </p>
        <div className="table-wrap" role="region" aria-label="Position-group index weights" tabIndex={0}>
          <table className="table" style={{ minWidth: 860 }}>
            <thead>
              <tr>
                <th scope="col">Group</th>
                {outfield[0].metric_ids.map((id) => (
                  <th scope="col" key={id}>{meta.metrics[id]?.name ?? id}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {outfield.map((group) => (
                <tr key={group.code}>
                  <td><strong>{group.label}</strong></td>
                  {group.metric_ids.map((id) => (
                    <td key={id}>{group.weights[id]?.toFixed(2) ?? "—"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {gk && (
          <>
            <h3>Goalkeeper weights</h3>
            <table>
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Weight</th>
                </tr>
              </thead>
              <tbody>
                {gk.metric_ids.map((id) => (
                  <tr key={id}>
                    <td>{meta.metrics[id]?.name ?? id}</td>
                    <td>{gk.weights[id]?.toFixed(2) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <h2>The normalization</h2>
        <p>
          A raw per-90 value is converted to a percentile within the player&rsquo;s position group
          and league tier this season:
        </p>
        <blockquote>
          P = (B + 0.5 × E) / N × 100
          <br />
          <span style={{ color: "var(--color-text-muted)" }}>
            where B is the number of qualifying peers below the player&rsquo;s value, E the number
            exactly equal, and N the total qualifying players in the group. Ties split the
            difference; this is the standard fractional-rank percentile.
          </span>
        </blockquote>
        <p>
          Percentiles, not z-scores — per-90 distributions are skewed and percentiles stay honest
          about that. A percentile of 87 means &ldquo;exceeds 87% of qualifying peers in this
          group.&rdquo;
        </p>

        <h2>Worked example — a real player, end to end</h2>
        <p>
          To show the arithmetic is real, here is a full walkthrough of a player currently in the
          dataset. The numbers below come from the same published percentile snapshot the profile
          page renders — nothing is invented for this example.
        </p>
        <p>
          <strong>Andrés Keller</strong> (Benfica, centre-back, 2025-26, 2,283 league minutes —
          comfortably past the 900-minute qualifying threshold). Each of his twelve outfield
          metrics was converted to a fractional-rank percentile within the Tier 2 centre-back
          cohort, then multiplied by the CB weight. The weighted sum is the Index:
        </p>
        <div className="table-wrap" role="region" aria-label="Andrés Keller worked example" tabIndex={0}>
          <table className="table" style={{ minWidth: 620 }}>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col">Percentile</th>
                <th scope="col">CB weight</th>
                <th scope="col">Contribution</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Progressive passes per 90</td><td>98.51</td><td>0.18</td><td>17.73</td></tr>
              <tr><td>Pressures per 90</td><td>97.01</td><td>0.15</td><td>14.55</td></tr>
              <tr><td>Tackles per 90</td><td>95.52</td><td>0.18</td><td>17.19</td></tr>
              <tr><td>Pass completion %</td><td>92.19</td><td>0.16</td><td>14.75</td></tr>
              <tr><td>Shots per 90</td><td>89.55</td><td>0.01</td><td>0.90</td></tr>
              <tr><td>Interceptions per 90</td><td>85.07</td><td>0.15</td><td>12.76</td></tr>
              <tr><td>Dispossessed per 90</td><td>77.61</td><td>0.04</td><td>3.10</td></tr>
              <tr><td>xG per 90</td><td>56.72</td><td>0.03</td><td>1.70</td></tr>
              <tr><td>Key passes per 90</td><td>53.73</td><td>0.01</td><td>0.54</td></tr>
              <tr><td>Goals per 90</td><td>52.24</td><td>0.02</td><td>1.04</td></tr>
              <tr><td>Progressive carries per 90</td><td>50.75</td><td>0.05</td><td>2.54</td></tr>
              <tr><td>xAG per 90</td><td>2.99</td><td>0.02</td><td>0.06</td></tr>
            </tbody>
            <tfoot>
              <tr>
                <th scope="row" colSpan={3}>Weighted sum (= Statlas Index)</th>
                <td><strong>86.87</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Rounded contributions are shown; the live value is computed from unrounded percentiles.
          You can reproduce this by opening Keller&rsquo;s profile (percentiles + index in the
          header), the weights above, and a calculator. Note that the 2.99 percentile for xAG is
          not a typo — it is exactly what the cohort comparison produced, and the low 0.02 weight
          limits its effect. If you spot any mismatch between this table and a number on the site,
          that is a bug — report it at data@statlas.com.
        </p>

        <h2>League tiers</h2>
        <p>
          Percentiles are computed within a league tier, not per league and not globally:
        </p>
        <ul>
          {meta.tiers.map((tier) => (
            <li key={tier.code}>
              <strong>{tier.label}</strong> — {tier.league_slugs.join(", ")}
            </li>
          ))}
        </ul>
        <p>
          Computing within a tier makes cross-league comparison within that tier meaningful while
          avoiding the distortion of mixing five elite leagues with second divisions. Because of
          the tier structure, percentiles are labelled with their tier and cannot be read as global
          rankings. xG uses one model per tier (Understat for Tier 1, FBref for Tiers 2–3) so no
          percentile mixes two xG models.
        </p>

        <h2>The qualifying threshold</h2>
        <p>
          A player receives an Index score after <strong>{meta.qualifying_minutes} league
          minutes</strong> in the current season (about ten full matches). Below that, per-90 rates —
          especially goals and xG — are too noisy to rank fairly. Below the threshold a player shows
          as &ldquo;pending qualification,&rdquo; never a low score. Minimum pool size for a
          percentile: {meta.min_pool_size} qualifying players in the group.
        </p>

        <h2>What the Index does not do</h2>
        <ul>
          <li>does not account for role within a system — a full-back asked to tuck in is compared to full-backs;</li>
          <li>does not weight quality of opposition, game state, or team strength;</li>
          <li>does not correct penalty kicks in the goals and xG inputs (a documented MVP simplification);</li>
          <li>is <strong>not a prediction</strong> of future performance, transfer value, or injury risk;</li>
          <li>is computed from per-90 output, not minutes-weighted contribution — volume is visible on the player page, deliberately not folded into the Index.</li>
        </ul>

        <h2>Data and refresh</h2>
        <p>
          {meta.weekly_refresh} Each recomputation creates a new immutable snapshot of percentile
          and index values; past snapshots are preserved and never rewritten, so a percentile you
          saw two weeks ago is still verifiable. Source attribution: per-90 statistics from FBref
          (Sports Reference), xG/xA for the Big-5 from Understat, event data where shown from
          StatsBomb Open Data.
        </p>

        <h2>Change control</h2>
        <p>
          Any change to the formula, weights, threshold, or grouping ships in the same commit as
          this page&rsquo;s update and a dated changelog entry. A formula change without its
          methodology update is treated as a failed change.
        </p>
      </div>
    </div>
  );
}
