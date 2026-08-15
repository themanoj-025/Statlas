"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { SimilarPlayer } from "@/lib/types";
import { formatNumber, percentileBand } from "@/lib/format";

export function SimilarPlayers({ playerId, playerName }: { playerId: number; playerName: string }) {
  const [players, setPlayers] = useState<SimilarPlayer[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
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
  }, [playerId]);

  return (
    <section className="card" aria-label="Similar players">
      <h2 className="card__title" style={{ fontSize: "var(--text-lg)" }}>
        Similar players
      </h2>
      <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "0 0 var(--space-3)" }}>
        Similarity basis: cosine similarity across {playerName}&rsquo;s percentile vector against
        players in the same position group and league tier, on the metrics present for both (a
        missing percentile is never treated as a zero).
      </p>

      {error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">
            We couldn&rsquo;t compute similar players right now — they rebuild on the next weekly
            refresh.
          </p>
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
            <li
              key={player.player_id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "var(--space-3)",
                padding: "var(--space-2) 0",
                borderBottom: "1px solid var(--color-divider)",
              }}
            >
              <span>
                {player.slug ? (
                  <Link href={`/players/${player.slug}`}>{player.name}</Link>
                ) : (
                  player.name
                )}
                <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                  {[player.club, player.league].filter(Boolean).join(" · ")}
                </span>
              </span>
              <span className="num" style={{ color: percentileBand(player.similarity * 100), fontWeight: 600 }}>
                {formatNumber(player.similarity * 100, 0)}% match
              </span>
            </li>
          ))}
        </ul>
      )}

      {players === null && !error && (
        <div role="status" aria-label="Loading similar players">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} style={{ padding: "var(--space-2) 0" }}>
              <span className="skeleton" style={{ display: "inline-block", width: "70%", height: 14 }} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
