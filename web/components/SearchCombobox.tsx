"use client";

import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { SearchResult } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { initials, positionGroupLabel } from "@/lib/format";

type Props = {
  autoFocus?: boolean;
  onSelect?: (result: SearchResult) => void;
  placeholder?: string;
};

export function SearchCombobox({ autoFocus, onSelect, placeholder }: Props) {
  const router = useRouter();
  const listboxId = useId();
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [status, setStatus] = useState<"idle" | "loading" | "empty" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const generationRef = useRef(0);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setStatus("idle");
      setOpen(false);
      return;
    }
    setStatus("loading");
    generationRef.current += 1;
    const gen = generationRef.current;
    try {
      const data = await api.playerSearch(q, 8);
      if (generationRef.current !== gen) return;
      setResults(data);
      setStatus(data.length ? "idle" : "empty");
      setActiveIndex(-1);
      setOpen(true);
    } catch (err) {
      if (generationRef.current !== gen) return;
      setStatus("error");
      setErrorMsg(err instanceof ApiError ? err.message : "search failed");
      setOpen(true);
    }
  }, []);

  const onInputChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(value), 300);
  };

  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    generationRef.current += 1;
  }, []);

  const select = (result: SearchResult) => {
    setOpen(false);
    setQuery("");
    setResults([]);
    if (onSelect) {
      onSelect(result);
    } else if (result.slug) {
      router.push(`/players/${result.slug}`);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (results.length ? (i + 1) % results.length : -1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (results.length ? (i - 1 + results.length) % results.length : -1));
    } else if (event.key === "Enter") {
      if (activeIndex >= 0 && results[activeIndex]) {
        event.preventDefault();
        select(results[activeIndex]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
      setResults([]);
      event.currentTarget.blur();
    }
  };

  const inputLabel = "Search players, clubs…";

  return (
    <div className="combobox">
      <Search
        className="combobox__icon"
        size={16}
        strokeWidth={1.5}
        aria-hidden="true"
      />
      <input
        id={inputId}
        className="input combobox__input"
        type="search"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-activedescendant={activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined}
        aria-autocomplete="list"
        aria-label={inputLabel}
        aria-busy={status === "loading"}
        autoComplete="off"
        autoFocus={autoFocus}
        placeholder={placeholder ?? "Search players, clubs… e.g. 'Haaland'"}
        value={query}
        onChange={(e) => onInputChange(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => {
          if (query.trim() && results.length) setOpen(true);
        }}
        onBlur={() => {
          setTimeout(() => setOpen(false), 150);
        }}
      />
      <label htmlFor={inputId} className="visually-hidden">
        {inputLabel}
      </label>

      {open && (
        <div id={listboxId} role="listbox" aria-label="Player search results" className="combobox__listbox">
          {status === "loading" && (
            <div className="combobox__hint" role="status">
              Searching…
            </div>
          )}

          {status === "empty" && (
            <div className="combobox__hint" role="status">
              No players found matching &ldquo;{query}&rdquo;. Try a club name or an alternate spelling —
              FBref spellings are used (e.g. &ldquo;de Bruyne&rdquo;). If the player is outside current
              data coverage, they won&rsquo;t appear (see the{" "}
              <a href="/data-coverage" onMouseDown={(e) => e.preventDefault()}>
                data coverage page
              </a>
              ).
            </div>
          )}

          {status === "error" && (
            <div className="combobox__hint" role="alert">
              Search is temporarily unavailable ({errorMsg}). Retry, or come back after the next weekly
              refresh (Wednesday 03:00 UTC).
            </div>
          )}

          {status === "idle" &&
            results.map((result, index) => (
              <div
                key={result.player_id}
                id={`${listboxId}-option-${index}`}
                role="option"
                aria-selected={index === activeIndex}
                className={`combobox__option ${index === activeIndex ? "combobox__option--active" : ""}`}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => select(result)}
                onMouseEnter={() => setActiveIndex(index)}
              >
                <span className="avatar-placeholder" style={{ width: 36, height: 36, fontSize: "var(--text-sm)" }} aria-hidden="true">
                  {initials(result.name)}
                </span>
                <span>
                  <span className="combobox__option-name">{result.name}</span>
                  <span className="combobox__option-meta" style={{ display: "block" }}>
                    {[result.club, result.league, positionGroupLabel(result.position_group)]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
