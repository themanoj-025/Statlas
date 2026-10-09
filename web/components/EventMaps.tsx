"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";
import type { EventCoverage, EventMatch } from "@/lib/types";
import { api } from "@/lib/api";
import { ShotMap } from "./ShotMap";
import { PassMap } from "./PassMap";
import { formatDate } from "@/lib/format";

type Tab = "shots" | "passes";

/**
 * Shot & pass maps section (Phase 3 — Part B). Coverage-gating is the FIRST
 * step (B1): the entry point renders only when data_coverage confirms the
 * competition/season AND match events exist for this player. When it does not,
 * the honest B4 note renders instead — a factual statement of what event data
 * Statlas currently holds, never a grayed-out "coming soon" that implies
 * universal coverage.
 */
export function EventMaps({
  playerId,
  playerName,
  coveredCompetitions,
  initialCoverage,
}: {
  playerId: number;
  playerName: string;
  coveredCompetitions: string[];
  initialCoverage?: EventCoverage | null;
}) {
  const [coverage, setCoverage] = useState<EventCoverage | null>(initialCoverage ?? null);
  const [matches, setMatches] = useState<EventMatch[]>([]);
  const [tab, setTab] = useState<Tab>("shots");
  const [loading, setLoading] = useState(!initialCoverage);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const [cov, matchRows] = await Promise.all([
        api.playerEventCoverage(playerId),
        api.playerEventMatches(playerId),
      ]);
      if (controller.signal.aborted) return;
      setCoverage(cov);
      setMatches(matchRows);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof Error ? err.message : "coverage query failed");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [playerId, attempt]);

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, [load]);

  const competitions =
    coverage?.competitions.map((c) => ({
      competition_id: c.competition_id,
      competition_name: c.competition_name,
      season: c.season,
    })) ?? [];

  const attribution = (
    <p className="statsbomb-attribution" role="note">
      Data by StatsBomb — open data (StatsBomb Public Data User Agreement; research use with
      attribution). Event coverage exists only for the competitions listed on the data coverage
      page; maps never imply more.
    </p>
  );

  return (
    <section className="card" style={{ marginTop: "var(--space-4)" }} aria-label="Shot and pass maps">
      <div className="section-head" style={{ marginTop: 0 }}>
        <h2 className="card__title">Shot &amp; pass maps</h2>
        {coverage?.competitions[0] && (
          <span className="chip chip--primary">
            {coverage.competitions[0].competition_name} · {coverage.competitions[0].season}
          </span>
        )}
      </div>

      {loading && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__body">Checking event-data coverage for {playerName}…</p>
        </div>
      )}

      {!loading && error && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__title">We couldn&rsquo;t check event-data coverage.</p>
          <p className="state-block__body">{error}</p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm" onClick={() => setAttempt((a) => a + 1)}>
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && !error && coverage && !coverage.has_coverage && (
        <div className="state-block state-block--sunken" role="status">
          <p className="state-block__body">
            <Activity size={14} aria-hidden="true" style={{ verticalAlign: "middle" }} />{" "}
            Event-level data for this player is not yet available. Statlas currently has match
            event data for{" "}
            {coveredCompetitions.length
              ? coveredCompetitions.join(", ")
              : "no competitions"}{" "}
            — shot and pass maps render only for players in those competitions, per the{" "}
            <a href="/data-coverage">data coverage page</a>.
          </p>
        </div>
      )}

      {!loading && !error && coverage?.has_coverage && (
        <>
          <div className="segmented" role="group" aria-label="Map type" style={{ marginBottom: "var(--space-3)" }}>
            <button type="button" className="segmented__button" aria-pressed={tab === "shots"} onClick={() => setTab("shots")}>
              Shots
            </button>
            <button type="button" className="segmented__button" aria-pressed={tab === "passes"} onClick={() => setTab("passes")}>
              Passes
            </button>
          </div>

          {tab === "shots" ? (
            <ShotMap playerId={playerId} playerName={playerName} competitions={competitions} matches={matches} />
          ) : (
            <PassMap playerId={playerId} playerName={playerName} competitions={competitions} matches={matches} />
          )}
          {attribution}
        </>
      )}
    </section>
  );
}
