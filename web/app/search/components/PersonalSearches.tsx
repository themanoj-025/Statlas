"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

export function PersonalSearches({
  onLoad,
  onShowResults,
  refreshToken,
  historyCount,
}: {
  onLoad: (qd: QueryDefinition) => void;
  onShowResults: (results: SearchResults) => void;
  refreshToken: boolean;
  historyCount: number;
}) {
  const [searches, setSearches] = useState<SavedSearchSummary[] | null>(null);
  const [history, setHistory] = useState<{ history_id: number; summary: string; executed_at: string; result_count: number; query_definition: QueryDefinition }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [busyRun, setBusyRun] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, h] = await Promise.all([api.savedSearches(), api.searchHistory(10)]);
      setSearches(s.searches);
      setHistory(h.entries);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load your saved searches.");
    }
  }, []);

  // Refresh ONLY the history list (a run/rerun logs a new entry server-side
  // but never changes the saved-searches list — reloading that here would race
  // with a concurrent delete).
  const refreshHistory = useCallback(async () => {
    try {
      const h = await api.searchHistory(10);
      setHistory(h.entries);
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, attempt, refreshToken]);

  const runSaved = async (searchId: number, qd: QueryDefinition) => {
    setBusyRun(searchId);
    setRunError(null);
    try {
      // The stored query is re-executed server-side against CURRENT data; the
      // fresh results are displayed directly (never stale).
      const res = await api.runSavedSearch(searchId, { limit: 25 });
      onLoad(qd);
      onShowResults(res.results);
      // Reflect the updated last_run_at in the saved list + the auto-logged
      // history entry (every real run is recorded server-side).
      setSearches((prev) =>
        prev
          ? prev.map((s) => (s.search_id === searchId ? { ...s, last_run_at: res.saved.last_run_at } : s))
          : prev
      );
      void refreshHistory();
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Could not run the saved search.");
    } finally {
      setBusyRun(null);
    }
  };

  const rerun = async (entry: { history_id: number; query_definition: QueryDefinition }) => {
    setRunError(null);
    try {
      const res = await api.rerunHistoryEntry(entry.history_id, { limit: 25 });
      onLoad(entry.query_definition);
      onShowResults(res.results);
      void refreshHistory(); // the re-run logs a NEW history entry
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Could not re-run that search.");
    }
  };

  const deleteSaved = async (searchId: number) => {
    if (!window.confirm("Delete this saved search? Your search history is not affected.")) return;
    try {
      await api.deleteSavedSearch(searchId);
      setSearches((prev) => (prev ? prev.filter((s) => s.search_id !== searchId) : prev));
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Could not delete the saved search.");
    }
  };

  if (error && searches === null) {
    return (
      <div className="state-block state-block--error" role="alert">
        <p className="state-block__body">{error}</p>
        <div className="state-block__actions">
          <button type="button" className="button button--sm" onClick={() => setAttempt((a) => a + 1)}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: "var(--space-4)" }}>
      {runError && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">{runError}</p>
        </div>
      )}

      <section className="card" aria-label="My saved searches">
        <div className="section-head">
          <h2 style={{ margin: 0 }}>My saved searches</h2>
        </div>
        {!searches ? (
          <p className="field__hint" role="status">
            Loading…
          </p>
        ) : searches.length === 0 ? (
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__body">
              No saved searches yet. Build a query above and hit <em>Save</em> — or start from a{" "}
              <a href="#presets">preset</a>.
            </p>
          </div>
        ) : (
          <ul className="saved-search-list">
            {searches.map((s) => (
              <li key={s.search_id} className="saved-search-list__item">
                <div>
                  <p className="preset-list__name">{s.name}</p>
                  {s.description && <p className="preset-list__rationale">{s.description}</p>}
                  <p className="field__hint">
                    {s.condition_count} condition{s.condition_count === 1 ? "" : "s"}
                    {s.last_run_at ? ` · last run ${relativeAndAbsolute(s.last_run_at)}` : " · never run"}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "var(--space-1)" }}>
                  <button
                    type="button"
                    className="button button--sm"
                    disabled={busyRun === s.search_id}
                    onClick={() => void runSaved(s.search_id, s.query_definition)}
                  >
                    <RotateCcw size={12} aria-hidden="true" /> Run
                  </button>
                  <button type="button" className="button button--sm button--ghost" aria-label={`Delete ${s.name}`} onClick={() => void deleteSaved(s.search_id)}>
                    <Trash2 size={13} aria-hidden="true" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card" aria-label="Search history">
        <div className="section-head">
          <h2 style={{ margin: 0 }}>History</h2>
          <span className="field__hint">last {history.length > 0 ? history.length : 0} runs</span>
        </div>
        {history.length === 0 ? (
          <p className="field__hint">
            Every query you run is logged here automatically — revisit it without having remembered to save
            it. Runs are kept per account, newest 50.
          </p>
        ) : (
          <ul className="history-list">
            {history.map((h) => (
              <li key={h.history_id} className="history-list__item">
                <div>
                  <p className="history-list__summary">{h.summary}</p>
                  <p className="field__hint">
                    {relativeAndAbsolute(h.executed_at)} · {h.result_count}{" "}
                    {h.result_count === 1 ? "result" : "results"} — results may differ from the original run
                    because data refreshes weekly
                  </p>
                </div>
                <button type="button" className="button button--sm button--secondary" onClick={() => void rerun(h)}>
                  <RotateCcw size={12} aria-hidden="true" /> Re-run
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
