"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import {
  ALERT_TYPE_LABELS,
  DIGEST_FREQUENCY_LABELS,
  type AlertType,
  type DigestFrequency,
  type WatchPreferences,
} from "@/lib/types";

const ALERT_TYPES: AlertType[] = [
  "percentile_movement",
  "club_change",
  "new_season_data",
  "data_coverage_change",
];

const ALERT_TYPE_DESCRIPTIONS: Record<AlertType, string> = {
  percentile_movement:
    "A watched metric moves 15+ percentile points between weekly snapshots (both snapshots above the qualification floor).",
  club_change: "A followed player's club changes between snapshots.",
  new_season_data: "The first qualifying snapshot of a new season arrives for a followed entity.",
  data_coverage_change:
    "Event-data coverage newly becomes available — or a data-quality flag is raised — for a followed entity.",
};

const DIGEST_FREQUENCIES: DigestFrequency[] = ["immediate", "daily_digest", "weekly_digest"];

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; prefs: WatchPreferences };

export function PreferencesClient() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [typePrefs, setTypePrefs] = useState<Record<AlertType, boolean>>({
    percentile_movement: true,
    club_change: true,
    new_season_data: true,
    data_coverage_change: true,
  });
  const [digest, setDigest] = useState<DigestFrequency>("immediate");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const prefs = await api.watchPreferences();
      setEmailEnabled(prefs.email_enabled);
      setTypePrefs({
        percentile_movement: prefs.alert_type_preferences.percentile_movement ?? true,
        club_change: prefs.alert_type_preferences.club_change ?? true,
        new_season_data: prefs.alert_type_preferences.new_season_data ?? true,
        data_coverage_change: prefs.alert_type_preferences.data_coverage_change ?? true,
      });
      setDigest(prefs.digest_frequency);
      setState({ kind: "ready", prefs });
    } catch (err) {
      setState({ kind: "error", message: err instanceof ApiError ? err.message : "Could not load preferences." });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      await api.updateWatchPreferences({
        email_enabled: emailEnabled,
        alert_type_preferences: typePrefs,
        digest_frequency: digest,
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save preferences.");
      setSaved(false);
    } finally {
      setSaving(false);
    }
  };

  if (state.kind === "loading") {
    return <div aria-busy="true" aria-label="Loading preferences">{[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 56, marginBottom: "var(--space-3)" }} />)}</div>;
  }
  if (state.kind === "error") {
    return (
      <div className="state-card" role="alert">
        <p>{state.message}</p>
        <button type="button" className="button" onClick={() => void load()}>Retry</button>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <fieldset className="prefs-fieldset">
        <legend>Email</legend>
        <label className="prefs-row">
          <span>
            <strong>Email alerts</strong>
            <span className="muted">
              Send alert emails for the trigger types enabled below. In-app notifications are
              always shown regardless.
            </span>
          </span>
          <input
            type="checkbox"
            checked={emailEnabled}
            onChange={(e) => setEmailEnabled(e.target.checked)}
          />
        </label>
      </fieldset>

      <fieldset className="prefs-fieldset">
        <legend>Alert types</legend>
        {ALERT_TYPES.map((type) => (
          <label key={type} className="prefs-row">
            <span>
              <strong>{ALERT_TYPE_LABELS[type]}</strong>
              <span className="muted">{ALERT_TYPE_DESCRIPTIONS[type]}</span>
            </span>
            <input
              type="checkbox"
              checked={typePrefs[type]}
              onChange={(e) => setTypePrefs((prev) => ({ ...prev, [type]: e.target.checked }))}
            />
          </label>
        ))}
      </fieldset>

      <fieldset className="prefs-fieldset">
        <legend>Delivery</legend>
        <div className="prefs-row">
          <span>
            <strong>How often</strong>
            <span className="muted">
              Immediate sends one email per alert; digests batch everything into a single,
              well-organized email per period.
            </span>
          </span>
          <div className="prefs-radios" role="radiogroup" aria-label="Digest frequency">
            {DIGEST_FREQUENCIES.map((f) => (
              <label key={f} className="prefs-radio">
                <input
                  type="radio"
                  name="digest_frequency"
                  value={f}
                  checked={digest === f}
                  onChange={() => setDigest(f)}
                />
                {DIGEST_FREQUENCY_LABELS[f]}
              </label>
            ))}
          </div>
        </div>
      </fieldset>

      {saved === true && (
        <p role="status" className="inline-message" style={{ color: "var(--color-success)" }}>
          Preferences saved — delivery will respect them immediately.
        </p>
      )}
      {error && (
        <p role="alert" className="inline-message" style={{ color: "var(--color-danger)" }}>
          {error}
        </p>
      )}

      <div style={{ marginTop: "var(--space-3)" }}>
        <button type="submit" className="button" disabled={saving}>
          {saving ? "Saving…" : "Save preferences"}
        </button>
        <Link href="/watchlist" className="button button--secondary" style={{ marginLeft: "var(--space-2)" }}>
          Back to watchlist
        </Link>
      </div>
    </form>
  );
}
