"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { SimilarPlayer, SimilarityExplanation } from "@/lib/types";
import { formatNumber, ordinal, percentileBand } from "@/lib/format";

/**
 * Similar players — nearest neighbours with a real "why" (Phase 6).
 *
 * Every result carries an `explanation` computed from the same percentile
 * vectors that produced the score (similarity-explanation-method.md):
 * matched strengths are the metrics that contributed most to the cosine
 * score where both players rank highly and sit close; key differences are
 * the largest percentile-point gaps with the stronger player stated.
 * All states are explicit: loading skeleton matching the list shape, the
 * empty state, a retry-capable error state, the no-meaningful-differences
 * case ("very similar across every measured metric"), and the visible
 * missing-data note listing excluded metrics and why.
 */
export function SimilarPlayers({ playerId, playerName }: { playerId: number; playerName: string }) {
  const [players, setPlayers] = useState<SimilarPlayer[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    fetch(`${process.env.NEXT_PUBLIC_STATLAS_API_URL}/api/v1/players/${playerId}/similar?limit=5`, {
      cache: "no-store",
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status));
        const data = (await res.json()) as SimilarPlayer[];
        if (!cancelled) setPlayers(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [playerId, attempt]);

  return (
    <section className="card" aria-label="Similar players">
      <h2 className="card__title" style={{ fontSize: "var(--text-lg)" }}>
        Similar players
      </h2>
      <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "0 0 var(--space-3)" }}>
        Similarity basis: cosine similarity across {playerName}&rsquo;s percentile vector against
        players in the same position group and league tier, on the metrics present for both (a
        missing percentile is never treated as a zero). Expand a player to see which metrics
        drove the match and where they diverge.
      </p>

      {error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">
            We couldn&rsquo;t compute similar players right now — they rebuild on the next weekly
            refresh.
          </p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm button--secondary" onClick={() => setAttempt((a) => a + 1)}>
              Try again
            </button>
          </div>
        </div>
      )}

      {players !== null && !players.length && !error && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__body">
            No comparable players yet — {playerName} needs a published percentile vector and at
            least five shared metrics with a peer to compute similarity.
          </p>
        </div>
      )}

      {players !== null && players.length > 0 && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {players.map((player) => (
            <li key={player.player_id} className="similar-player">
              <div className="similar-player__row">
                <span>
                  {player.slug ? (
                    <Link href={`/players/${player.slug}`}>{player.name}</Link>
                  ) : (
                    player.name
                  )}
                  <span className="similar-player__meta">
                    {[player.club, player.league].filter(Boolean).join(" · ")}
                  </span>
                </span>
                <span className="num" style={{ color: percentileBand(player.similarity * 100), fontWeight: 600 }}>
                  {formatNumber(player.similarity * 100, 0)}% match
                </span>
              </div>
              <details className="similar-player__why">
                <summary>
                  Why {formatNumber(player.similarity * 100, 0)}%?
                </summary>
                <ExplanationBreakdown
                  explanation={player.explanation}
                  anchorName={playerName}
                  peerName={player.name}
                />
              </details>
            </li>
          ))}
        </ul>
      )}

      {players === null && !error && (
        <div role="status" aria-label="Loading similar players">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="similar-player">
              <div className="similar-player__row">
                <span className="skeleton" style={{ display: "inline-block", width: "55%", height: 14 }} />
                <span className="skeleton" style={{ display: "inline-block", width: 72, height: 14 }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ExplanationBreakdown({
  explanation,
  anchorName,
  peerName,
}: {
  explanation: SimilarityExplanation;
  anchorName: string;
  peerName: string;
}) {
  const { matched_strengths, key_differences, excluded_metrics, excluded_reason } = explanation;

  return (
    <div className="similar-player__explanation">
      <h3 className="similar-player__subtitle">Matched strengths</h3>
      {matched_strengths.length ? (
        <ul className="similar-player__list">
          {matched_strengths.map((m) => (
            <li key={m.metric} className="similar-player__item">
              <ArrowUp
                className="similar-player__icon similar-player__icon--up"
                size={14}
                strokeWidth={2}
                aria-hidden="true"
              />
              <span>
                Both rank highly in <strong>{m.metric_name}</strong> —{" "}
                <span className="num">
                  {ordinal(Math.round(m.player_a_percentile))} vs{" "}
                  {ordinal(Math.round(m.player_b_percentile))} percentile
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="similar-player__note">
          No shared standout strengths — the match is driven by consistent alignment across
          mid-range metrics.
        </p>
      )}

      <h3 className="similar-player__subtitle">Key differences</h3>
      {key_differences.length ? (
        <ul className="similar-player__list">
          {key_differences.map((m) => {
            const strongerIsAnchor = m.stronger_player === "player_a";
            const strongerName = strongerIsAnchor ? anchorName : peerName;
            const strongerPct = strongerIsAnchor ? m.player_a_percentile : m.player_b_percentile;
            const weakerPct = strongerIsAnchor ? m.player_b_percentile : m.player_a_percentile;
            return (
              <li key={m.metric} className="similar-player__item">
                <ArrowDown
                  className="similar-player__icon similar-player__icon--down"
                  size={14}
                  strokeWidth={2}
                  aria-hidden="true"
                />
                <span>
                  <strong>{strongerName}</strong> is stronger in <strong>{m.metric_name}</strong> —{" "}
                  <span className="num">
                    {ordinal(Math.round(strongerPct))} vs {ordinal(Math.round(weakerPct))} percentile
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="similar-player__note">
          These players have very similar profiles across every measured metric.
        </p>
      )}

      {excluded_metrics.length > 0 && (
        <p className="similar-player__note similar-player__note--excluded" role="note">
          {excluded_metrics.length} metric{excluded_metrics.length === 1 ? "" : "s"} not compared —{" "}
          {excluded_metrics.map((m) => m.metric_name).join(", ")}: {excluded_reason}.
        </p>
      )}
    </div>
  );
}
