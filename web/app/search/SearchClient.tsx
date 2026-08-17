"use client";

import Link from "next/link";
import { ChevronDown, Plus, RotateCcw, Save, Search, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AddToShortlist } from "@/components/AddToShortlist";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { formatNumber, positionGroupLabel, relativeAndAbsolute, tierLabel } from "@/lib/format";
import type {
  ConditionOperator,
  Meta,
  QueryDefinition,
  SavedSearchSummary,
  SearchCondition,
  SearchPreset,
  SearchResultEntry,
  SearchResults,
  ShortlistSummary,
} from "@/lib/types";

const MAX_CONDITIONS = 8;

// ---------------------------------------------------------------------------
// Operator options per condition type (grammar: query-builder-scope.md §2)
// ---------------------------------------------------------------------------

const PERCENTILE_OPERATORS: { value: ConditionOperator; label: string }[] = [
  { value: "percentile_gte", label: "at least (≥)" },
  { value: "percentile_lte", label: "at most (≤)" },
  { value: "percentile_between", label: "between" },
];

const RAW_OPERATORS: { value: ConditionOperator; label: string }[] = [
  { value: "gte", label: "at least (≥)" },
  { value: "lte", label: "at most (≤)" },
  { value: "between", label: "between" },
  { value: "eq", label: "exactly (=)" },
];

const TIERS = [
  { value: "", label: "All tiers" },
  { value: "tier_1", label: "Tier 1" },
  { value: "tier_2", label: "Tier 2" },
  { value: "tier_3", label: "Tier 3" },
];

const SORTS = [
  { value: "index", label: "Statlas Index" },
  { value: "minutes", label: "Minutes" },
  { value: "age", label: "Age" },
  { value: "name", label: "Name" },
];

// ---------------------------------------------------------------------------

export function SearchClient({ meta, presets }: { meta: Meta; presets: SearchPreset[] }) {
  const { status } = useAuth();
  const signedIn = status === "signed-in";

  // --- builder state -------------------------------------------------------
  const [positionGroup, setPositionGroup] = useState("");
  const [leagueTier, setLeagueTier] = useState("");
  const [ageMax, setAgeMax] = useState("");
  const [conditions, setConditions] = useState<SearchCondition[]>([
    { metric: "si_prgp_p90", operator: "percentile_gte", value: 70, value_max: null },
    { metric: "minutes_played", operator: "gte", value: 1500, value_max: null },
  ]);

  // --- live preview + results ----------------------------------------------
  const [preview, setPreview] = useState<SearchResults | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState("index");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [saved, setSaved] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const queryDefinition = useMemo<QueryDefinition>(
    () => ({
      position_group: positionGroup ? [positionGroup] : null,
      league_tier: leagueTier || null,
      age_max: ageMax ? Number(ageMax) : null,
      conditions,
      condition_logic: "AND",
    }),
    [positionGroup, leagueTier, ageMax, conditions]
  );

  const refreshPersonal = useCallback(async () => {
    if (status !== "signed-in") return;
    try {
      const h = await api.searchHistory(5);
      setHistoryCount(h.entries.length);
    } catch {
      /* non-fatal for the builder */
    }
  }, [status]);

  useEffect(() => {
    void refreshPersonal();
  }, [refreshPersonal, saved]);

  // Live preview: debounced, small limit, never logged to history.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (conditions.length === 0) {
      setPreview(null);
      return;
    }
    setPreviewing(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.executeSearch(queryDefinition, {
          limit: 1,
          offset: 0,
          log_history: false,
        });
        setPreview(res);
      } catch {
        setPreview(null);
      } finally {
        setPreviewing(false);
      }
    }, 450);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryDefinition]);

  const run = async () => {
    setRunning(true);
    setRunError(null);
    try {
      const res = await api.executeSearch(queryDefinition, {
        limit: 25,
        offset: 0,
        sort_by: sortBy,
        sort_dir: sortDir,
        log_history: signedIn,
      });
      setResults(res);
      if (signedIn) {
        setHistoryCount((n) => n + 1);
        setSaved((v) => v);
      }
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Could not run the query.");
    } finally {
      setRunning(false);
    }
  };

  const usePreset = (preset: SearchPreset) => loadQuery(preset.query_definition);

  const updateCondition = (index: number, patch: Partial<SearchCondition>) => {
    setConditions((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  };

  const removeCondition = (index: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== index));
  };

  const addCondition = () => {
    setConditions((prev) => [
      ...prev,
      { metric: "si_tkl_p90", operator: "percentile_gte", value: 60, value_max: null },
    ]);
  };

  const clearAll = () => {
    setConditions([]);
    setPreview(null);
    setResults(null);
  };

  const loadQuery = (qd: QueryDefinition) => {
    setPositionGroup(qd.position_group?.[0] ?? "");
    setLeagueTier(qd.league_tier ?? "");
    setAgeMax(qd.age_max ? String(qd.age_max) : "");
    setConditions(
      qd.conditions.map((c) => ({
        metric: c.metric,
        operator: c.operator,
        value: c.value,
        value_max: c.value_max ?? null,
      }))
    );
    setResults(null);
  };

  return (
    <div style={{ display: "grid", gap: "var(--space-4)", marginTop: "var(--space-4)" }}>
      {/* ------------------------------------------------------------------ */}
      {/* Query builder                                                      */}
      {/* ------------------------------------------------------------------ */}
      <section className="card" aria-label="Query builder">
        <div className="section-head">
          <h2 style={{ margin: 0 }}>Conditions</h2>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
            {conditions.length > 0 && (
              <button type="button" className="button button--sm button--ghost" onClick={clearAll}>
                <Trash2 size={13} aria-hidden="true" /> Clear all
              </button>
            )}
            {conditions.length < MAX_CONDITIONS && (
              <button type="button" className="button button--sm" onClick={addCondition}>
                <Plus size={13} aria-hidden="true" /> Add condition
              </button>
            )}
          </div>
        </div>

        {/* Scalar filters */}
        <div className="query-builder__scalars">
          <div className="field">
            <label className="field__label" htmlFor="qb-position">
              Position group
            </label>
            <select
              id="qb-position"
              className="select"
              value={positionGroup}
              onChange={(e) => setPositionGroup(e.target.value)}
            >
              <option value="">All positions</option>
              {meta.position_groups.map((g) => (
                <option key={g.code} value={g.code}>
                  {g.plural}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="qb-tier">
              League tier
            </label>
            <select
              id="qb-tier"
              className="select"
              value={leagueTier}
              onChange={(e) => setLeagueTier(e.target.value)}
            >
              {TIERS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="qb-age">
              Age max <span className="field__hint">(optional)</span>
            </label>
            <input
              id="qb-age"
              className="input"
              type="number"
              min={15}
              max={60}
              value={ageMax}
              placeholder="e.g. 23"
              onChange={(e) => setAgeMax(e.target.value)}
            />
          </div>
        </div>

        {conditions.length === 0 ? (
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__body">
              Add at least one condition to build a query, or pick a{" "}
              <a href="#presets">curated preset</a> below.
            </p>
          </div>
        ) : (
          <ul className="query-builder__conditions" aria-label="Query conditions">
            {conditions.map((cond, index) => (
              <ConditionRow
                key={index}
                index={index}
                cond={cond}
                meta={meta}
                onChange={(patch) => updateCondition(index, patch)}
                onRemove={() => removeCondition(index)}
              />
            ))}
          </ul>
        )}

        <div className="query-builder__footer">
          <div className="query-builder__preview" role="status" aria-live="polite">
            {previewing ? (
              <>
                <span className="skeleton" style={{ display: "inline-block", width: 90, height: 14 }} />
                <span className="field__hint">Counting…</span>
              </>
            ) : preview ? (
              <p>
                <strong>{preview.total.toLocaleString()}</strong>{" "}
                {preview.total === 1 ? "player matches" : "players match"}{" "}
                <span className="field__hint">
                  · every result has ≥ {preview.qualifying_minutes} minutes (qualification floor)
                </span>
              </p>
            ) : null}
          </div>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
            <div className="field" style={{ margin: 0 }}>
              <label className="field__label" htmlFor="qb-sort">
                Sort by
              </label>
              <select
                id="qb-sort"
                className="select select--sm"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="button button--sm button--secondary"
              aria-label="Toggle sort direction"
              onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
            >
              {sortDir === "desc" ? "High → low" : "Low → high"}
            </button>
            <button type="button" className="button button--sm" disabled={running || conditions.length === 0} onClick={() => void run()}>
              <Search size={13} aria-hidden="true" /> {running ? "Running…" : "Search"}
            </button>
            {signedIn && conditions.length > 0 && <SaveSearchButton queryDefinition={queryDefinition} onSaved={() => setSaved((v) => !v)} />}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Results                                                            */}
      {/* ------------------------------------------------------------------ */}
      {runError && (
        <div className="state-block state-block--error" role="alert">
          <p className="state-block__body">{runError}</p>
          <div className="state-block__actions">
            <button type="button" className="button button--sm" onClick={() => void run()}>
              Retry
            </button>
          </div>
        </div>
      )}

      {results && (
        <ResultsSection
          results={results}
          sortBy={sortBy}
          sortDir={sortDir}
          onSort={(by, dir) => {
            setSortBy(by);
            setSortDir(dir);
            setRunning(true);
            api
              .executeSearch(queryDefinition, { limit: 25, offset: 0, sort_by: by, sort_dir: dir, log_history: signedIn })
              .then(setResults)
              .catch((err) => setRunError(err instanceof ApiError ? err.message : "Could not sort results."))
              .finally(() => setRunning(false));
          }}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Presets + saved + history                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="search-side" style={{ display: "grid", gap: "var(--space-4)" }}>
        <section className="card" id="presets" aria-label="Curated presets">
          <div className="section-head">
            <h2 style={{ margin: 0 }}>Presets</h2>
          </div>
          <p className="field__hint">
            Curated starting points, each with a real query that runs against current data. Load one,
            then tweak it.
          </p>
          <ul className="preset-list">
            {presets.map((preset) => (
              <li key={preset.id} className="preset-list__item">
                <div>
                  <p className="preset-list__name">{preset.name}</p>
                  <p className="preset-list__rationale">{preset.rationale}</p>
                </div>
                <button type="button" className="button button--sm button--secondary" onClick={() => usePreset(preset)}>
                  Use preset
                </button>
              </li>
            ))}
          </ul>
        </section>

        {signedIn ? (
          <PersonalSearches
            onLoad={loadQuery}
            onShowResults={setResults}
            refreshToken={saved}
            historyCount={historyCount}
          />
        ) : (
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__title">Saved searches &amp; history</p>
            <p className="state-block__body">
              Sign in to save queries for reuse and to revisit what you&rsquo;ve searched.{" "}
              <Link href="/login">Sign in</Link> or{" "}
              <Link href="/register">create a free account</Link> — the free tier includes 5 saved
              searches.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// One condition row
// ---------------------------------------------------------------------------

function ConditionRow({
  index,
  cond,
  meta,
  onChange,
  onRemove,
}: {
  index: number;
  cond: SearchCondition;
  meta: Meta;
  onChange: (patch: Partial<SearchCondition>) => void;
  onRemove: () => void;
}) {
  const metric = meta.metrics[cond.metric];
  const isPercentile = cond.operator.startsWith("percentile");
  const operators = isPercentile ? PERCENTILE_OPERATORS : RAW_OPERATORS;
  const rowId = `cond-${index}`;

  // Metric options grouped by position applicability (same sets as the Radar
  // tool: outfield vs GK), plus a Raw values group for minutes.
  const outfieldMetrics = meta.position_groups.filter((g) => g.code !== "GK").flatMap((g) => g.metric_ids);
  const gkMetrics = meta.position_groups.find((g) => g.code === "GK")?.metric_ids ?? [];
  const allOutfield = Array.from(new Set(outfieldMetrics));
  const allGk = Array.from(new Set(gkMetrics));
  const shown = metric ? (allOutfield.includes(cond.metric) ? allOutfield : allGk) : allOutfield;

  return (
    <li className="query-builder__condition">
      <div className="query-builder__condition-metric">
        <label className="field__label" htmlFor={`${rowId}-metric`}>
          Metric
        </label>
        <select
          id={`${rowId}-metric`}
          className="select"
          value={cond.metric}
          onChange={(e) => {
            const next = e.target.value;
            // Switching between percentile/raw metrics resets the operator to
            // something valid for the new metric's condition type.
            const isRaw = next === "minutes_played";
            onChange({
              metric: next,
              operator: isRaw ? "gte" : "percentile_gte",
              value: isRaw ? 1500 : 70,
              value_max: null,
            });
          }}
        >
          <optgroup label="Outfield">
            {allOutfield.map((mid) => (
              <option key={mid} value={mid}>
                {meta.metrics[mid]?.name ?? mid}
              </option>
            ))}
          </optgroup>
          <optgroup label="Goalkeeper">
            {allGk.map((mid) => (
              <option key={mid} value={mid}>
                {meta.metrics[mid]?.name ?? mid}
              </option>
            ))}
          </optgroup>
          <optgroup label="Raw values">
            <option value="minutes_played">Minutes played</option>
          </optgroup>
        </select>
      </div>

      <div className="query-builder__condition-op">
        <label className="field__label" htmlFor={`${rowId}-op`}>
          {isPercentile ? "Percentile" : "Value"}
        </label>
        <select
          id={`${rowId}-op`}
          className="select"
          value={cond.operator}
          onChange={(e) => onChange({ operator: e.target.value as ConditionOperator, value_max: null })}
        >
          {operators.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>
      </div>

      <div className="query-builder__condition-value">
        <label className="field__label" htmlFor={`${rowId}-value`}>
          {isPercentile ? "Percentile" : cond.metric === "minutes_played" ? "Minutes" : "Value"}
        </label>
        <input
          id={`${rowId}-value`}
          className="input"
          type="number"
          min={isPercentile ? 0 : 0}
          max={isPercentile ? 100 : undefined}
          value={Number.isFinite(cond.value) ? cond.value : ""}
          onChange={(e) => onChange({ value: e.target.value === "" ? 0 : Number(e.target.value) })}
        />
      </div>

      {(cond.operator === "between" || cond.operator === "percentile_between") && (
        <div className="query-builder__condition-value">
          <label className="field__label" htmlFor={`${rowId}-max`}>
            and
          </label>
          <input
            id={`${rowId}-max`}
            className="input"
            type="number"
            min={isPercentile ? 0 : 0}
            max={isPercentile ? 100 : undefined}
            value={Number.isFinite(cond.value_max ?? 0) ? (cond.value_max ?? 0) : ""}
            onChange={(e) => onChange({ value_max: e.target.value === "" ? 0 : Number(e.target.value) })}
          />
        </div>
      )}

      <div className="query-builder__condition-note">
        {metric ? (
          <span className="field__hint">
            {metric.name} — {metric.definition}
          </span>
        ) : (
          <span className="field__hint">Raw minutes played across the season.</span>
        )}
      </div>

      <button type="button" className="button button--sm button--ghost query-builder__remove" aria-label={`Remove condition ${index + 1}`} onClick={onRemove}>
        <X size={13} aria-hidden="true" />
      </button>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Save-current-query (auth required — honest upsell handled by the API)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Results — leaderboard-style rows with the per-condition values shown, plus
// per-row and bulk "Add to shortlist" (the Phase 7 ↔ Phase 8 integration).
// ---------------------------------------------------------------------------

function ResultsSection({
  results,
  sortBy,
  sortDir,
  onSort,
}: {
  results: SearchResults;
  sortBy: string;
  sortDir: "asc" | "desc";
  onSort: (by: string, dir: "asc" | "desc") => void;
}) {
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);

  if (results.total === 0) {
    const most = results.diagnostics?.most_restrictive;
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">0 players match this query</p>
        {most && (
          <p className="state-block__body">
            The most restrictive condition is{" "}
            <strong>
              {most.metric_name} {most.operator === "percentile_gte" ? "≥" : most.operator === "percentile_lte" ? "≤" : ""}{" "}
              {most.value}
              {most.operator.startsWith("percentile") ? "th percentile" : ""}
            </strong>{" "}
            — only {most.passing_count} qualifying {most.passing_count === 1 ? "player passes" : "players pass"} it. Try
            lowering the threshold or removing that condition.
          </p>
        )}
        <p className="state-block__body">{results.note}</p>
      </div>
    );
  }

  return (
    <section className="card" aria-label="Search results">
      <div className="section-head">
        <h2 style={{ margin: 0 }}>
          Results <span className="field__hint">({results.total.toLocaleString()})</span>
        </h2>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
          <select
            className="select select--sm"
            aria-label="Sort results"
            value={sortBy}
            onChange={(e) => onSort(e.target.value, sortDir)}
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                Sort: {s.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="button button--sm button--secondary"
            onClick={() => onSort(sortBy, sortDir === "desc" ? "asc" : "desc")}
          >
            {sortDir === "desc" ? "High → low" : "Low → high"}
          </button>
          <div style={{ position: "relative" }}>
            <button type="button" className="button button--sm" aria-expanded={bulkOpen} onClick={() => setBulkOpen((v) => !v)}>
              <Plus size={13} aria-hidden="true" /> Add all to shortlist
            </button>
            {bulkOpen && <BulkAddPanel playerIds={results.entries.map((e) => e.player_id)} onClose={() => setBulkOpen(false)} onMessage={setBulkMessage} />}
          </div>
        </div>
      </div>

      {bulkMessage && (
        <p className="field__hint" role={bulkMessage.startsWith("Added") ? "status" : "alert"}>
          {bulkMessage}
        </p>
      )}

      <p className="field__hint">{results.note}</p>

      <div className="table-wrap">
        <table className="table" aria-label={`${results.total} matching players`}>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col">Pos</th>
              <th scope="col">Age</th>
              <th scope="col">Minutes</th>
              <th scope="col">Index</th>
              <th scope="col">Why they matched</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {results.entries.map((entry) => (
              <ResultRow key={entry.player_id} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>

      {results.has_more && (
        <p className="field__hint">
          Showing the first {results.entries.length} of {results.total.toLocaleString()} — the API is paginated
          (this view shows the top of the sort).
        </p>
      )}
    </section>
  );
}

function ResultRow({ entry }: { entry: SearchResultEntry }) {
  return (
    <tr>
      <td>
        <Link href={entry.slug ? `/players/${entry.slug}` : "#"} className="shortlist-entry__name">
          {entry.name}
        </Link>
        <span className="shortlist-entry__meta">
          {[entry.club, entry.league].filter(Boolean).join(" · ")}
        </span>
      </td>
      <td>{entry.position_group ? positionGroupLabel(entry.position_group) : "—"}</td>
      <td>{entry.age ?? "—"}</td>
      <td>{Math.round(entry.minutes).toLocaleString()}</td>
      <td>{entry.index !== null && entry.index !== undefined ? formatNumber(entry.index, 1) : "—"}</td>
      <td>
        <ul className="result-conditions" aria-label="Condition values">
          {entry.condition_values.map((cv) => (
            <li key={`${cv.metric}-${cv.operator}`} className="result-conditions__item">
              <span className="field__hint">{cv.metric_name}:</span>{" "}
              {cv.actual === null || cv.actual === undefined ? (
                <em className="field__hint">no data</em>
              ) : cv.condition_type === "percentile" ? (
                <strong>{formatNumber(cv.actual, 0)}th pct</strong>
              ) : (
                <strong>{formatNumber(cv.actual, cv.metric === "minutes_played" ? 0 : 2)}</strong>
              )}
            </li>
          ))}
        </ul>
      </td>
      <td>
        <AddToShortlist playerId={entry.player_id} playerName={entry.name} compact />
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Bulk add — one deliberate action, then a real shortlist selector
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Saved searches + history (auth required)
// ---------------------------------------------------------------------------

function PersonalSearches({
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
