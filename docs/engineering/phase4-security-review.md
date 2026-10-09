# Statlas — Phase 4 Security Review (2026-08-14)

Scope: the new payment (Stripe) and API-key surfaces added in Phase 4, per
Part D3 of the Phase 4 prompt. Each item lists what is enforced and the test
that proves it. All assertions run in CI (`pytest`), not just documented.

---

## D3-1: No Stripe secret keys or API-key generation logic client-side

- Stripe secret keys live only in server env vars (`STRIPE_SECRET_KEY`,
  `STRIPE_WEBHOOK_SECRET`), read by `app/config.py`. The web app never sees
  them: checkout is initiated via `POST /api/v1/billing/checkout` on the API
  layer, which returns the hosted Checkout URL. No `stripe.js` publishable key
  is embedded anywhere in `web/`.
- API-key *generation* happens server-side (`app/api_keys.py`) using
  `secrets.token_urlsafe`; the dashboard only receives the one-time reveal.
- **Evidence:** `grep` for `sk_live`/`sk_test`/`pk_live` in `web/` returns
  nothing; checkout flow test (`tests/test_billing.py::test_checkout_creates_session_and_grants_on_webhook`)
  shows the client only receives a URL.

## D3-2: Webhook signature verification genuinely enforced

- `app/billing.py: verify_webhook_signature` uses `stripe.Webhook.construct_event`
  against `STRIPE_WEBHOOK_SECRET`. An unsigned payload or a tampered signature
  raises `WebhookVerificationError` → HTTP 400 with no side effects.
- **Evidence (tests, real signature path):**
  - `tests/test_billing.py::test_unsigned_webhook_rejected` — no
    `stripe-signature` header → 400.
  - `tests/test_billing.py::test_tampered_webhook_rejected` — payload signed,
    then modified byte-for-byte → 400, and zero `webhook_events` rows written.

## D3-3: API keys stored hashed, one-time reveal

- Keys are `sl_<prefix>.<32 random bytes>`. Only the SHA-256 hash is stored
  (`app/api_keys.py`, `auth.hash_token`); the plaintext exists exactly once,
  at creation, in the API response. The dashboard lists prefixes only.
- **Evidence:** `tests/test_public_api.py::test_key_created_with_one_time_reveal_and_hashed_storage`
  asserts the DB row holds the hash and never the raw key.

## Additional hardening in this phase

| Area | Implementation |
|---|---|
| Session tokens | Stored as SHA-256 hashes (`session_tokens.token_hash`); expiry + revocation enforced at lookup (`auth.user_from_session`) |
| Passwords | PBKDF2-HMAC-SHA256, 600k iterations, per-user salt — never plaintext (`auth.hash_password`) |
| Webhook idempotency | `webhook_events.event_id` UNIQUE; replays recorded as duplicates, never re-processed (`tests/test_billing.py::test_webhook_idempotent_replay`) |
| Grace period | `invoice.payment_failed` sets `past_due` + 7-day grace window; access retained, never abruptly cut |
| End-of-period retention | `customer.subscription.deleted` keeps access until `current_period_end`, then revokes |
| Public API auth | Bearer key resolved + revoked keys rejected (`tests/test_public_api.py::test_revoked_key_fails`, `test_rotate_mints_new_key_and_revokes_old`) |
| Rate limiting | Per-key sliding window with `X-RateLimit-*` headers; limits from `pricing.json` (`tests/test_public_api.py::test_rate_limit_429_after_cap`) |
| Assistant guardrails | Per-user rate limit + hard quota cap (`tests/test_assistant.py::test_assistant_rate_limit`, `test_assistant_quota_hard_cap`) |
| CORS | Credentials enabled only for the web origin; methods limited to GET/POST/OPTIONS |

## Known limitations / production upgrades (documented, not hidden)

1. **In-memory rate limiter** (`app/api/assistant_views._hits`,
   `app/api/public_views._hits`) — fine for single-instance dev and small
   scale; a multi-instance deployment must move to Redis (shared counters).
2. **Cookie secure flag** is env-gated (`STATLAS_COOKIE_SECURE=true` on https
   deployments) — must be enabled in production.
3. **Live Stripe/Anthropic runs** require real keys (test-mode Stripe keys,
   an Anthropic API key). The integration code paths are key-gated and the
   signature/idempotency/grace-period logic is tested against test-mode
   fixtures; a live end-to-end checkout is a Part E manual gate.
4. **Concurrency on webhook idempotency** — the DB unique constraint is the
   final arbiter (a race between two identical events fails one insert);
   single-instance processing means this is safe today.

## Conclusion

All Part D3 items are enforced with automated tests in CI. No findings
outstanding. Items 1–3 above are deployment configuration, not code defects,
and are tracked in `docs/suite/Deployment.md` + `.env.example`.
