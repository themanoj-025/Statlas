/** Shortlist sub-components: EntryRow, StatusControl, PriorityControl, TagControl, NoteControl. */

'use client'


function EntryRow({
  entry,
  onMutated,
  onError,
}: {
  entry: ShortlistEntryDetail;
  onMutated: () => void;
  onError: (msg: string) => void;
}) {
  const [removing, setRemoving] = useState(false);

  const remove = async () => {
    if (!window.confirm(`Remove ${entry.name} from this shortlist? Their notes, tags and status history are kept for audit.`)) return;
    setRemoving(true);
    try {
      await api.removeEntry(entry.entry_id);
      onMutated();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not remove the player.");
      setRemoving(false);
    }
  };

  return (
    <tr>
      <td>
        <Link href={entry.slug ? `/players/${entry.slug}` : "#"} className="shortlist-entry__name">
          {entry.name}
        </Link>
        <span className="shortlist-entry__meta">
          {[entry.club, positionGroupLabel(entry.position_group), entry.league].filter(Boolean).join(" · ")}
          {entry.index !== null && entry.index !== undefined && (
            <> · Index {formatNumber(entry.index, 1)}</>
          )}
        </span>
      </td>
      <td>
        <StatusControl entry={entry} onMutated={onMutated} onError={onError} />
      </td>
      <td>
        <PriorityControl entry={entry} onMutated={onMutated} onError={onError} />
      </td>
      <td>
        <TagControl entry={entry} onMutated={onMutated} onError={onError} />
      </td>
      <td>
        <NoteControl entry={entry} onMutated={onMutated} onError={onError} />
      </td>
      <td>
        <span className="shortlist-entry__added">{relativeAndAbsolute(entry.added_at) ?? "—"}</span>
      </td>
      <td>
        <div style={{ display: "flex", gap: "var(--space-2)", justifyContent: "flex-end" }}>
          <GenerateReport
            playerId={entry.player_id}
            playerName={entry.name}
            shortlistEntryId={entry.entry_id}
            compact
          />
          <button
            type="button"
            className="button button--sm button--ghost"
            aria-label={`Remove ${entry.name}`}
            disabled={removing}
            onClick={() => void remove()}
          >
            <Trash2 size={14} aria-hidden="true" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Status control — deliberate, not accidental-click-prone (Phase 7 C2/D2).
// A separate "Change" action opens an inline panel with the target selector
// and an OPTIONAL reason note (captured in status_history.reason_note).
// ---------------------------------------------------------------------------

function StatusControl({
  entry,
  onMutated,
  onError,
}: {
  entry: ShortlistEntryDetail;
  onMutated: () => void;
  onError: (msg: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState<EntryStatus>(entry.status);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apply = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.changeEntryStatus(entry.entry_id, target, reason.trim() || null);
      setOpen(false);
      setReason("");
      onMutated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change the status.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="status-control">
      <span className={`${STATUS_CHIP_CLASS[entry.status]} status-control__chip`}>{STATUS_LABELS[entry.status]}</span>
      <button type="button" className="button button--sm button--secondary" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        Change
      </button>
      {open && (
        <div className="status-control__panel" role="group" aria-label={`Change status of ${entry.name}`}>
          <label className="field__label" htmlFor={`status-${entry.entry_id}`}>
            Move to
          </label>
          <select
            id={`status-${entry.entry_id}`}
            className="select"
            value={target}
            onChange={(e) => setTarget(e.target.value as EntryStatus)}
          >
            {STATUS_ORDER.filter((s) => s !== entry.status).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          <label className="field__label" htmlFor={`reason-${entry.entry_id}`}>
            Reason <span className="field__hint">(optional — recorded in history)</span>
          </label>
          <input
            id={`reason-${entry.entry_id}`}
            className="input"
            type="text"
            value={reason}
            maxLength={1000}
            placeholder="e.g. Fee demands too high"
            onChange={(e) => setReason(e.target.value)}
          />
          {error && (
            <p className="field__hint" role="alert" style={{ color: "var(--color-danger)" }}>
              {error}
            </p>
          )}
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="button" className="button button--sm" onClick={() => void apply()} disabled={busy}>
              {busy ? "Saving…" : "Apply"}
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

// ---------------------------------------------------------------------------
// Priority — low-stakes, applies immediately on select.
// ---------------------------------------------------------------------------

function PriorityControl({
  entry,
  onMutated,
  onError,
}: {
  entry: ShortlistEntryDetail;
  onMutated: () => void;
  onError: (msg: string) => void;
}) {
  const [value, setValue] = useState<EntryPriority>(entry.priority);

  const apply = async (next: string) => {
    setValue(next as EntryPriority);
    try {
      await api.setEntryPriority(entry.entry_id, next || null);
      onMutated();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not set the priority.");
      setValue(entry.priority);
    }
  };

  // Priority is low-stakes and reversible — an immediate-apply select is the
  // right friction level (unlike status, which stays a deliberate action).
  return (
    <select
      className="select select--sm"
      aria-label={`Priority for ${entry.name}`}
      value={value ?? ""}
      onChange={(e) => void apply(e.target.value)}
    >
      <option value="">—</option>
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
  );
}

// ---------------------------------------------------------------------------
// Tags — chips with removal + add with the user's OWN autocomplete suggestions.
// ---------------------------------------------------------------------------

function TagControl({
  entry,
  onMutated,
  onError,
}: {
  entry: ShortlistEntryDetail;
  onMutated: () => void;
  onError: (msg: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [text, setText] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const fetchSuggestions = async (prefix: string) => {
    if (!prefix.trim()) {
      setSuggestions([]);
      return;
    }
    try {
      const res = await api.tagSuggestions(prefix);
      setSuggestions(res.tags.filter((t) => !entry.tags.includes(t)));
    } catch {
      setSuggestions([]);
    }
  };

  const add = async (tag: string) => {
    const trimmed = (tag || text).trim();
    if (!trimmed || entry.tags.includes(trimmed.toLowerCase())) return;
    setBusy(true);
    try {
      await api.addEntryTag(entry.entry_id, trimmed);
      setText("");
      setSuggestions([]);
      onMutated();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not add the tag.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (tag: string) => {
    try {
      await api.removeEntryTag(entry.entry_id, tag);
      onMutated();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not remove the tag.");
    }
  };

  return (
    <div className="tag-control">
      {entry.tags.length > 0 && (
        <ul className="tag-control__list" aria-label={`Tags for ${entry.name}`}>
          {entry.tags.map((tag) => (
            <li key={tag}>
              <span className="chip chip--tag">
                {tag}
                <button
                  type="button"
                  className="tag-control__remove"
                  aria-label={`Remove tag ${tag}`}
                  onClick={() => void remove(tag)}
                >
                  <X size={11} aria-hidden="true" />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="tag-control__add">
          <input
            className="input input--sm"
            type="text"
            value={text}
            maxLength={64}
            placeholder="e.g. left-footed"
            aria-label={`New tag for ${entry.name}`}
            onChange={(e) => {
              setText(e.target.value);
              void fetchSuggestions(e.target.value);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") void add(text);
            }}
          />
          <button type="button" className="button button--sm" disabled={!text.trim() || busy} onClick={() => void add(text)}>
            <Plus size={13} aria-hidden="true" /> Add
          </button>
          {suggestions.length > 0 && (
            <ul className="tag-control__suggestions" aria-label="Tag suggestions">
              {suggestions.map((s) => (
                <li key={s}>
                  <button type="button" className="button button--sm button--ghost" onClick={() => void add(s)}>
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <button type="button" className="button button--sm button--ghost" onClick={() => setAdding(true)}>
          <Plus size={12} aria-hidden="true" /> Tag
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Notes — preview, expandable full list with relative+absolute timestamps
// (Phase 7 D1), and inline add.
// ---------------------------------------------------------------------------

function NoteControl({
  entry,
  onMutated,
  onError,
}: {
  entry: ShortlistEntryDetail;
  onMutated: () => void;
  onError: (msg: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);

  const add = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api.addEntryNote(entry.entry_id, text);
      setText("");
      setAdding(false);
      onMutated();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Could not add the note.");
    } finally {
      setBusy(false);
    }
  };

  const latest = entry.notes[0];

  return (
    <div className="note-control">
      {entry.notes.length > 0 ? (
        <>
          <button type="button" className="button button--sm button--ghost" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            {entry.notes.length} note{entry.notes.length === 1 ? "" : "s"} {open ? "▲" : "▼"}
          </button>
          {!open && latest && (
            <p className="note-control__preview">
              {latest.note_text.slice(0, 90)}
              {latest.note_text.length > 90 ? "…" : ""}{" "}
              <span className="note-control__when">— {relativeAndAbsolute(latest.created_at)}</span>
            </p>
          )}
        </>
      ) : (
        <span className="field__hint">No notes yet</span>
      )}
      {open && (
        <ul className="note-control__list" aria-label={`Notes for ${entry.name}`}>
          {entry.notes.map((note) => (
            <li key={note.id}>
              <p className="note-control__text">{note.note_text}</p>
              <p className="note-control__when">{relativeAndAbsolute(note.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="note-control__add">
          <textarea
            className="input"
            rows={2}
            value={text}
            maxLength={4000}
            aria-label={`New note for ${entry.name}`}
            placeholder="Observation, meeting note, match watched…"
            onChange={(e) => setText(e.target.value)}
          />
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="button" className="button button--sm" disabled={!text.trim() || busy} onClick={() => void add()}>
              {busy ? "Saving…" : "Add note"}
            </button>
            <button type="button" className="button button--sm button--secondary" onClick={() => setAdding(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="button button--sm button--ghost" onClick={() => setAdding(true)}>
          <Plus size={12} aria-hidden="true" /> Note
        </button>
      )}
    </div>
  );
}
