"use client";

import type { Meta, SearchResultEntry, SearchCondition, ConditionOperator, QueryDefinition } from "@/lib/types";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";

function SaveSearchButton({ queryDefinition, onSaved }: { queryDefinition: QueryDefinition; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.saveSearch(name.trim(), queryDefinition, description.trim() || null);
      setOpen(false);
      setName("");
      setDescription("");
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the search.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ position: "relative" }}>
      <button type="button" className="button button--sm button--secondary" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <Save size={13} aria-hidden="true" /> Save
      </button>
      {open && (
        <div className="save-search-panel" role="group" aria-label="Save this query">
          <div className="field">
            <label className="field__label" htmlFor="save-search-name">
              Name
            </label>
            <input
              id="save-search-name"
              className="input"
              type="text"
              value={name}
              maxLength={128}
              placeholder="e.g. U23 progressive midfielders"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void save();
              }}
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="save-search-desc">
              Description <span className="field__hint">(optional)</span>
            </label>
            <textarea
              id="save-search-desc"
              className="input"
              rows={2}
              value={description}
              maxLength={2000}
              placeholder="What is this query for?"
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && (
            <p className="field__hint" role="alert" style={{ color: "var(--color-danger)" }}>
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="button" className="button button--sm" disabled={!name.trim() || busy} onClick={() => void save()}>
              {busy ? "Saving…" : "Save search"}
            </button>
            <button type="button" className="button button--sm button--secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
