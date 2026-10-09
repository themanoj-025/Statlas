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
import {
  BulkAddPanel,
  ConditionRow,
  PersonalSearches,
  ResultRow,
  ResultsSection,
  SaveSearchButton,
} from "./components";

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
