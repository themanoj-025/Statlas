"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

function BulkAddPanel({
  playerIds,
  onClose,
  onMessage,
}: {
  playerIds: number[];
  onClose: () => void;
  onMessage: (msg: string) => void;
}) {
  const [shortlists, setShortlists] = useState<ShortlistSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .workspace()
      .then((o) => setShortlists(o.shortlists))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load your shortlists."))
      .finally(() => setLoading(false));
  }, []);

  const addAll = async (shortlistId: number, name: string) => {
    setBusyId(shortlistId);
    setError(null);
    let added = 0;
    let skipped = 0;
    try {
      for (const playerId of playerIds) {
        try {
          await api.addToShortlist(shortlistId, playerId);
          added += 1;
        } catch (err) {
          if (err instanceof ApiError && err.status === 409) skipped += 1;
          else throw err;
        }
      }
      onMessage(`Added ${added} ${added === 1 ? "player" : "players"} to ${name}${skipped ? ` (${skipped} already there)` : ""}.`);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add players.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="bulk-add-panel" role="group" aria-label="Add all results to a shortlist">
      {loading && <p className="field__hint">Loading your shortlists…</p>}
      {error && (
        <p className="field__hint" role="alert" style={{ color: "var(--color-danger)" }}>
          {error}
        </p>
      )}
      {!loading && shortlists && (
        <>
          {shortlists.length === 0 ? (
            <p className="field__hint">No shortlists yet — create one from the workspace.</p>
          ) : (
            <ul className="bulk-add-panel__list">
              {shortlists.map((sl) => (
                <li key={sl.shortlist_id}>
                  <button
                    type="button"
                    className="button button--sm button--secondary"
                    disabled={busyId !== null}
                    onClick={() => void addAll(sl.shortlist_id, sl.name)}
                  >
                    {busyId === sl.shortlist_id ? "Adding…" : `${sl.name} (${sl.entry_count})`}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <button type="button" className="button button--sm button--ghost" onClick={onClose}>
        Cancel
      </button>
    </div>
  );
}
