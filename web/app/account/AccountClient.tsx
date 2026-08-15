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

export function AccountClient() {
  const { user, status, subscription, refresh, logout } = useAuth();
  const [portalBusy, setPortalBusy] = useState(false);
  const [portalError, setPortalError] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

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

  return (
    <div style={{ display: "grid", gap: "var(--space-4)", marginTop: "var(--space-4)" }}>
      <section className="card" aria-label="Profile">
        <h2 className="card__title" style={{ marginTop: 0 }}>
          Profile
        </h2>
        <p style={{ margin: 0 }}>
          <strong>{user?.email}</strong> · plan: <span className="chip">{sub?.plan ?? "free"}</span>
        </p>
        <button type="button" className="button button--secondary" style={{ marginTop: "var(--space-3)" }} onClick={() => void doLogout()} disabled={signingOut}>
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </section>

      <section className="card" aria-label="Subscription">
        <h2 className="card__title" style={{ marginTop: 0 }}>
          Subscription
        </h2>

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
    </div>
  );
}
