"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";

const PLANS = [
  {
    name: "Free",
    price: "€0",
    cadence: "forever",
    recommended: false,
    cta: "Start free",
    features: [
      "Full player profiles with radar, percentiles and the Statlas Index",
      "Leaderboards (top 50 rows per leaderboard)",
      "3 player comparisons per day",
      "Trend history (last 5 snapshots)",
      "10 assistant queries per month",
      "Methodology and data coverage pages",
    ],
  },
  {
    name: "Pro",
    price: "€7",
    cadence: "/month · €60/year",
    recommended: true,
    cta: "Go Pro",
    features: [
      "Unlimited leaderboard rows",
      "Unlimited comparisons and trend history (10-snapshot window)",
      "Unlimited scouting workspace (shortlists, notes, tags, status pipeline)",
      "Shot and pass maps for covered competitions",
      "200 assistant queries per month",
      "CSV export and PDF scout-report export",
      "Embed widgets (up to 10 active embeds)",
      "Priority support",
    ],
  },
];

export function PricingClient() {
  const { user, status } = useAuth();
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCheckout = async () => {
    setCheckoutBusy(true);
    setError(null);
    try {
      const origin = window.location.origin;
      const { url } = await api.checkout(
        `${origin}/account?checkout=success`,
        `${origin}/pricing?checkout=cancelled`
      );
      // Abandonment path: Stripe returns the user to the cancel_url (the
      // pricing page) — no broken state.
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start checkout — try again.");
      setCheckoutBusy(false);
    }
  };

  return (
    <>
      <div className="grid" style={{ marginTop: "var(--space-5)" }}>
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className="card grid__span-6"
            style={
              plan.recommended
                ? { borderTop: "3px solid var(--color-accent)", position: "relative" }
                : undefined
            }
          >
            {plan.recommended && (
              <span
                className="chip chip--accent"
                style={{ position: "absolute", top: "-10px", right: "var(--space-4)" }}
              >
                Recommended
              </span>
            )}
            <h2 style={{ margin: 0 }}>{plan.name}</h2>
            <p
              style={{
                margin: "var(--space-1) 0 var(--space-3)",
                fontSize: "var(--text-2xl)",
                fontWeight: 700,
                fontFamily: "var(--font-data)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {plan.price}
              <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", fontWeight: 400 }}>
                {" "}
                {plan.cadence}
              </span>
            </p>
            <ul
              style={{
                margin: 0,
                padding: 0,
                listStyle: "none",
                display: "grid",
                gap: "var(--space-2)",
                marginBottom: "var(--space-4)",
              }}
            >
              {plan.features.map((feature) => (
                <li key={feature} style={{ fontSize: "var(--text-sm)" }}>
                  {feature}
                </li>
              ))}
            </ul>
            {plan.recommended ? (
              status === "loading" ? (
                <button type="button" className="button" style={{ width: "100%" }} disabled>
                  Checking account…
                </button>
              ) : status === "signed-in" ? (
                <button
                  type="button"
                  className="button"
                  style={{ width: "100%" }}
                  onClick={() => void startCheckout()}
                  disabled={checkoutBusy}
                >
                  {checkoutBusy ? "Opening checkout…" : "Go Pro"}
                </button>
              ) : (
                <Link href="/login" className="button" style={{ width: "100%", textAlign: "center" }}>
                  Sign in to upgrade
                </Link>
              )
            ) : (
              <Link
                href={status === "signed-in" ? "/compare" : "/register"}
                className="button button--secondary"
                style={{ width: "100%", textAlign: "center" }}
              >
                {plan.cta}
              </Link>
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="state-block state-block--error" role="alert" style={{ marginTop: "var(--space-4)" }}>
          <p className="state-block__body">{error}</p>
        </div>
      )}

      <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
        Prices verified at checkout. VAT may apply. Billing is handled by Stripe Checkout — card
        details never touch Statlas servers. Subscription management, including cancellation, is
        available from account settings; canceled subscriptions keep Pro access until the end of the
        paid period.
      </p>
    </>
  );
}
