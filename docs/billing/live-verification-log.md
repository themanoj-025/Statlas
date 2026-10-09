# Billing — Live Verification Log (Phase 4 Part E / Final Launch Part A1)

*Created: 2026-08-15. Purpose: real, captured evidence from a live Stripe
test-mode run — or an explicit BLOCKED status. Per the launch-execution
prompt's hard constraints: **no simulated or fabricated results are ever
recorded here.** If a check cannot run, it is logged BLOCKED with the exact
credential/action required.*

---

## Status: BLOCKED — Stripe test-mode credentials not present

Checked `2026-08-15` in the build environment:

| Credential | Status |
|---|---|
| `STRIPE_SECRET_KEY` (test mode) | ❌ not set |
| `STRIPE_WEBHOOK_SECRET` (test mode) | ❌ not set |
| `STRIPE_PRICE_PRO_MONTHLY` | ❌ not set |
| `STRIPE_BILLING_PORTAL_ENABLED` | ❌ not set |

**BLOCKED — Stripe test-mode credentials required. Founder action: retrieve
from the Stripe dashboard (test mode) and set as environment variables.**

- Stripe dashboard → Developers → API keys → *Publishable/Secret* (test mode,
  `sk_test_…`).
- Stripe dashboard → Developers → Webhooks → create endpoint
  `POST {API_BASE}/api/v1/billing/webhook` subscribing to
  `checkout.session.completed`, `invoice.payment_failed`,
  `customer.subscription.deleted`, `customer.subscription.updated`; copy the
  signing secret (`whsec_…`) into `STRIPE_WEBHOOK_SECRET`.
- Create the "Statlas Pro" product/price (€7/month, `price_…`) per
  `docs/billing/pricing-config.md` §"Stripe dashboard setup".
- Set `STRIPE_BILLING_PORTAL_ENABLED=true` after enabling the Billing Portal.

The billing code itself is key-gated by design: with these unset, endpoints
return an explicit "billing not configured" state rather than failing
mid-checkout (`.env.example` documents this), so the product is not in a
broken state — it is simply not live-verifiable here.

---

## Test plan — executes verbatim once credentials are present

Each check below records **actual output** (webhook logs, `subscriptions`
table state before/after, captured API responses) appended to this file with a
timestamp. None of the rows below are results; they are the plan.

### T1 — Happy-path checkout → immediate access
1. Start API (`uvicorn app.api.main:app`) + web, both with Stripe env vars set.
2. Sign up / log in as a fresh user; confirm `plan == free` in the DB.
3. Go to `/pricing` → Pro → Checkout (hosted Stripe Checkout, test mode).
4. Pay with test card `4242 4242 4242 4242` (any future expiry, any CVC).
5. Assert, with captured evidence:
   - Redirect back to success URL **without manual refresh** → the UI already
     reflects Pro (optimistic update).
   - A `checkout.session.completed` event arrives at the webhook endpoint,
     signature-verified (log line `webhook verified`), processed once.
   - `subscriptions` table: row present with `status` active, correct
     `current_period_end`.
   - `has_pro_access(user_id)` returns `True` from the same session that
     already shows Pro (no double-source divergence).

### T2 — Webhook idempotency
1. Replay the exact same `checkout.session.completed` payload (Stripe
   dashboard → webhook → resend, or `stripe trigger`).
2. Assert **no duplicate effects**: subscription count for the user is still
   exactly 1; no double access flag; webhook log shows the event id already
   processed and skipped.

### T3 — Failed payment → grace period (not immediate revocation)
1. Create a subscription, then update the customer's default payment method to
   the declining test card `4000 0000 0000 0002`.
2. Trigger `invoice.payment_failed` (test-mode webhook send).
3. Assert, with captured state:
   - Access is **NOT** revoked: `has_pro_access` still `True`.
   - `subscriptions` row shows the grace state (`grace_period_end` set,
     ~7 days per `app/billing.py`).
   - UI surfaces the "Payment issue — update your card by [date]" messaging.

### T4 — Grace period → recovery
1. From T3 state, update the payment method back to `4242 4242 4242 4242`
   (via the billing portal) and trigger a successful invoice payment.
2. Assert: grace state cleared, access retained, no interruption.

### T5 — Cancellation → end-of-period retention
1. Cancel the subscription (billing portal or Stripe dashboard).
2. Assert `customer.subscription.deleted` webhook processed: `status` →
   cancelled, but `has_pro_access` keeps returning `True` until
   `current_period_end` (per `app/billing.py` — end-of-period access
   retention), then `False` after the period ends.
3. Confirm the downgrade experience: saved comparisons/permalinks behave as
   documented (see `docs/billing/pricing-config.md` and the account page copy).

### T6 — Signature verification (security gate)
1. Send a tampered/unsigned webhook payload to
   `/api/v1/billing/webhook` (no `stripe-signature` header, and a forged one).
2. Assert both are rejected (4xx) and **no** state change occurs — this is the
   D3 "tampered payload rejected" test repeated live.

---

## Result log

*Append here after each run. Format: date · test id · outcome (PASS/FAIL) ·
evidence (log excerpt / table snapshot / captured response). Never write
PASS without captured evidence.*
