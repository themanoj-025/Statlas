# Statlas — Pricing Configuration & Stripe Mapping

Date: 2026-08-14 · Phase 4 — Part A1.

**Single source of truth:** `app/config/pricing.json`. Every feature gate,
quota, and upsell reads it — never scattered magic strings. This file documents
how that config maps to the Stripe dashboard objects (Products/Prices), which
must be created by hand once per environment.

## Tier definitions (from the Constitution §1 business model)

| Plan | Price | What it unlocks | Limits (pricing.json) |
|---|---|---|---|
| `free` | €0 | Full player pages, leaderboards (top 50), 3 comparisons/day, trend window 5, 10 assistant queries/month | `leaderboard_rows: 50`, `comparisons_per_day: 3`, `trend_window: 5`, `assistant_queries_per_period: 10`, `embeds_active: 0`, `api_rate_limit_per_minute: 0` |
| `pro` | €7/month (€60/year) | Unlimited leaderboards + comparisons, trend window 10, shot/pass maps, 200 assistant queries/month, CSV + PDF export, 10 embeds | `leaderboard_rows: null`, `trend_window: 10`, `assistant_queries_per_period: 200`, `embeds_active: 10`, `api_rate_limit_per_minute: 0` |
| `api_business` | €49/month | Everything in Pro + public API access | `assistant_queries_per_period: 1000`, `embeds_active: null`, `api_rate_limit_per_minute: 120` |

Notes:
- `null` = unlimited within the tier.
- The assistant quota is a **hard cap** — no silent overage billing (the
  documented model per Phase 4 Part B3: users are blocked at the cap with the
  reset date stated).
- The public API is *not included* in free/pro — `api_rate_limit_per_minute: 0`
  produces an explicit 403 with upgrade copy, never silence.

## Stripe dashboard setup (one-time, per environment)

For each environment (dev/test mode, then production), create:

1. **Product "Statlas Pro"** with a monthly price (recurring, €7) and an
   annual price (recurring, €60, 1 year interval).
2. **Product "Statlas API Business"** with a monthly price (€49).
3. Record the price ids in the environment:

   ```bash
   STRIPE_PRICE_PRO_MONTHLY=price_xxx   # the monthly Pro price id
   # annual + API prices are optional for v1 (single checkout path)
   ```

4. Configure the webhook endpoint in the Stripe dashboard to
   `POST {API_BASE}/api/v1/billing/webhook`, subscribing to:
   - `checkout.session.completed`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
   Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
5. Enable the **Billing Portal** in the Stripe dashboard and set
   `STRIPE_BILLING_PORTAL_ENABLED=true`.

## Env vars consumed

| Var | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | API secret (server-side only — never client-side) |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification |
| `STRIPE_PRICE_PRO_MONTHLY` | The Pro monthly price id used by checkout |
| `STRIPE_BILLING_PORTAL_ENABLED` | Portal availability flag |

## How limits are consumed

- `app/config.py: plan_limits(plan)` — the single accessor every gate uses.
- `app/auth.py: has_pro_access()` — access decisions (subscriptions table).
- `app/billing.py` — checkout/webhook/portal.
- `app/assistant.py` — quota limits per plan.
- `app/api_keys.py: api_rate_limit_for_plan` — public API rate limits.

## Change process

A change to tier boundaries touches exactly two places, in the same commit:
`app/config/pricing.json` and this doc. The Stripe price objects are only
updated if the *price amount* changes (boundary changes like "top 100 rows
instead of 50" need no Stripe change).
