"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { ApiKeys } from "./ApiKeys";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString(undefined, { dateStyle: "medium" });
}

const TIMEZONES = [
  "UTC",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Europe/Madrid",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "America/Sao_Paulo",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Australia/Sydney",
];

export function AccountClient() {
  const { user, status, subscription, refresh, logout } = useAuth();
  const [portalBusy, setPortalBusy] = useState(false);
  const [portalError, setPortalError] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  // Profile state
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [tz, setTz] = useState(user?.timezone ?? "");
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);

  // Password state
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSaving, setPwSaving] = useState(false);

  // Email verification state
  const [verifyMsg, setVerifyMsg] = useState<string | null>(null);
  const [verifySending, setVerifySending] = useState(false);

  // Account deletion state
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState<string | null>(null);
  const [deleteSaving, setDeleteSaving] = useState(false);

  if (status === "loading") {
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__body">Loading your account…</p>
      </div>
    );
  }

  if (status === "signed-out") {
    return (
      <div className="state-block state-block--sunken" role="status">
        <p className="state-block__title">Not signed in</p>
        <p className="state-block__body">
          <Link href="/login">Sign in</Link> to see your subscription and API keys, or{" "}
          <Link href="/register">create a free account</Link>.
        </p>
      </div>
    );
  }

  const sub = subscription;
  const graceDate = formatDate(sub?.grace_period_end ?? null);
  const periodDate = formatDate(sub?.current_period_end ?? null);

  const openPortal = async () => {
    setPortalBusy(true);
    setPortalError(null);
    try {
      const { url } = await api.billingPortal(window.location.origin + "/account");
      window.location.href = url;
    } catch (err) {
      setPortalError(err instanceof ApiError ? err.message : "Could not open the billing portal.");
      setPortalBusy(false);
    }
  };

  const doLogout = async () => {
    setSigningOut(true);
    await logout();
  };

  const saveProfile = async () => {
    setProfileSaving(true);
    setProfileMsg(null);
    try {
      await api.updateProfile({
        display_name: displayName || null,
        timezone: tz || null,
      });
      setProfileMsg("Profile updated.");
      await refresh();
    } catch (err) {
      setProfileMsg(err instanceof ApiError ? err.message : "Could not update profile.");
    }
    setProfileSaving(false);
  };

  const changePassword = async () => {
    setPwSaving(true);
    setPwMsg(null);
    setPwError(null);
    try {
      await api.changePassword(currentPw, newPw);
      setPwMsg("Password changed.");
      setCurrentPw("");
      setNewPw("");
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : "Could not change password.");
    }
    setPwSaving(false);
  };

  const requestVerify = async () => {
    setVerifySending(true);
    setVerifyMsg(null);
    try {
      await api.requestEmailVerification();
      setVerifyMsg("Verification link sent. Check your email.");
    } catch (err) {
      setVerifyMsg(err instanceof ApiError ? err.message : "Could not send verification.");
    }
    setVerifySending(false);
  };

  const deleteAccount = async () => {
    setDeleteSaving(true);
    setDeleteMsg(null);
    try {
      await api.deleteAccount();
      setDeleteMsg("Account scheduled for deletion in 30 days. Sign in to cancel.");
    } catch (err) {
      setDeleteMsg(err instanceof ApiError ? err.message : "Could not delete account.");
    }
    setDeleteSaving(false);
  };

  return (
    <div style={{ display: "grid", gap: "var(--space-4)", marginTop: "var(--space-4)" }}>
      {/* Profile */}
      <section className="card" aria-label="Profile">
        <h2 className="card__title" style={{ marginTop: 0 }}>Profile</h2>
        <p style={{ margin: 0 }}>
          <strong>{user?.email}</strong> · plan: <span className="chip">{sub?.plan ?? "free"}</span>
          {user?.email_verified_at ? (
            <span className="chip" style={{ marginLeft: "var(--space-2)", background: "var(--color-success-muted, #d4edda)" }}>Verified</span>
          ) : (
            <button
              type="button"
              className="button button--sm button--ghost"
              style={{ marginLeft: "var(--space-2)" }}
              onClick={() => void requestVerify()}
              disabled={verifySending}
            >
              {verifySending ? "Sending…" : "Verify email"}
            </button>
          )}
        </p>
        {verifyMsg && <p className="field__hint" role="status">{verifyMsg}</p>}

        <div style={{ marginTop: "var(--space-3)", display: "grid", gap: "var(--space-2)", maxWidth: 400 }}>
          <label className="field" htmlFor="display-name">
            <span className="field__label">Display name</span>
            <input
              id="display-name"
              className="input"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional display name"
              maxLength={128}
            />
          </label>
          <label className="field" htmlFor="timezone">
            <span className="field__label">Timezone</span>
            <select
              id="timezone"
              className="input"
              value={tz}
              onChange={(e) => setTz(e.target.value)}
            >
              <option value="">System default</option>
              {TIMEZONES.map((z) => <option key={z} value={z}>{z}</option>)}
            </select>
          </label>
          <div>
            <button
              type="button"
              className="button button--sm"
              onClick={() => void saveProfile()}
              disabled={profileSaving}
            >
              {profileSaving ? "Saving…" : "Save profile"}
            </button>
            {profileMsg && <span className="field__hint" style={{ marginLeft: "var(--space-2)" }} role="status">{profileMsg}</span>}
          </div>
        </div>

        <button
          type="button"
          className="button button--secondary"
          style={{ marginTop: "var(--space-3)" }}
          onClick={() => void doLogout()}
          disabled={signingOut}
        >
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </section>

      {/* Security */}
      <section className="card" aria-label="Security">
        <h2 className="card__title" style={{ marginTop: 0 }}>Security</h2>
        <div style={{ display: "grid", gap: "var(--space-2)", maxWidth: 400 }}>
          <label className="field" htmlFor="current-pw">
            <span className="field__label">Current password</span>
            <input
              id="current-pw"
              className="input"
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          <label className="field" htmlFor="new-pw">
            <span className="field__label">New password (min 8 characters)</span>
            <input
              id="new-pw"
              className="input"
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              minLength={8}
              autoComplete="new-password"
            />
          </label>
          <div>
            <button
              type="button"
              className="button button--sm"
              onClick={() => void changePassword()}
              disabled={pwSaving || !currentPw || !newPw}
            >
              {pwSaving ? "Changing…" : "Change password"}
            </button>
            {pwMsg && <span className="field__hint" style={{ marginLeft: "var(--space-2)" }} role="status">{pwMsg}</span>}
            {pwError && <span className="field__hint" style={{ marginLeft: "var(--space-2)", color: "var(--color-danger)" }} role="alert">{pwError}</span>}
          </div>
        </div>
      </section>

      {/* Subscription */}
      <section className="card" aria-label="Subscription">
        <h2 className="card__title" style={{ marginTop: 0 }}>Subscription</h2>

        {!sub?.billing_configured && (
          <div className="state-block state-block--sunken" role="status">
            <p className="state-block__body">
              Billing is not configured on this deployment yet — upgrades are unavailable here.
              See the pricing page for the planned tiers.
            </p>
          </div>
        )}

        {sub?.billing_configured && (
          <>
            <p style={{ margin: 0 }}>
              {sub.has_pro ? (
                <>Pro access is active{periodDate ? ` until ${periodDate}` : ""}.</>
              ) : (
                <>You are on the free tier. <Link href="/pricing">Upgrade to Pro</Link> for unlimited leaderboards, full trend history and shot/pass maps.</>
              )}
            </p>

            {sub.status === "past_due" && graceDate && (
              <div className="state-block state-block--error" role="alert" style={{ marginTop: "var(--space-3)" }}>
                <p className="state-block__title">Payment issue</p>
                <p className="state-block__body">
                  We couldn&rsquo;t charge your card. Update your payment method by{" "}
                  <strong>{graceDate}</strong> to keep Pro access — nothing is cut off immediately.
                </p>
              </div>
            )}

            {sub.status === "canceled" && (
              <div className="state-block state-block--sunken" role="status" style={{ marginTop: "var(--space-3)" }}>
                <p className="state-block__body">
                  Your subscription is canceled{periodDate ? ` — Pro access continues until ${periodDate} (end of the paid period), then reverts to free` : ""}.
                  Saved comparisons and permalinks remain visible; Pro-only features (embeds, CSV export, full trend history) stop at that date.
                </p>
              </div>
            )}

            <div style={{ marginTop: "var(--space-3)", display: "grid", gap: "var(--space-2)" }}>
              {sub.portal_enabled ? (
                <button type="button" className="button" onClick={() => void openPortal()} disabled={portalBusy}>
                  {portalBusy ? "Opening billing portal…" : "Manage billing — update card, invoices, cancel"}
                </button>
              ) : (
                <p className="field__hint">
                  The billing portal is not enabled on this deployment yet. Contact support to update
                  your payment method.
                </p>
              )}
              {portalError && (
                <p className="field__hint" role="alert" style={{ color: "var(--color-danger)" }}>
                  {portalError}
                </p>
              )}
            </div>
          </>
        )}

        {sub?.has_pro && (
          <p className="field__hint" style={{ marginTop: "var(--space-3)" }}>
            Cancellation: you keep Pro until the end of the paid period — no immediate cut-off.
          </p>
        )}
      </section>

      <ApiKeys />

      {/* Danger zone */}
      <section className="card" aria-label="Account deletion" style={{ borderLeft: "3px solid var(--color-danger)" }}>
        <h2 className="card__title" style={{ marginTop: 0, color: "var(--color-danger)" }}>Danger zone</h2>
        <p className="field__hint">
          Deleting your account schedules it for permanent removal in 30 days. You can cancel
          the deletion by signing in during that period. All your shortlists, saved searches,
          reports, and watches will be permanently deleted.
        </p>
        {!deleteConfirm ? (
          <button
            type="button"
            className="button button--danger button--sm"
            onClick={() => setDeleteConfirm(true)}
          >
            Delete my account
          </button>
        ) : (
          <div style={{ display: "grid", gap: "var(--space-2)", maxWidth: 400 }}>
            <p style={{ margin: 0, fontWeight: 600 }}>Are you sure? This cannot be undone after 30 days.</p>
            <div style={{ display: "flex", gap: "var(--space-2)" }}>
              <button
                type="button"
                className="button button--danger button--sm"
                onClick={() => void deleteAccount()}
                disabled={deleteSaving}
              >
                {deleteSaving ? "Deleting…" : "Yes, delete my account"}
              </button>
              <button
                type="button"
                className="button button--secondary button--sm"
                onClick={() => { setDeleteConfirm(false); setDeleteMsg(null); }}
              >
                Cancel
              </button>
            </div>
            {deleteMsg && <p className="field__hint" role="status">{deleteMsg}</p>}
          </div>
        )}
      </section>
    </div>
  );
}
