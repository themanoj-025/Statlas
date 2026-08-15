# Public API — Live Verification Log (Phase 4 Part E / Final Launch Part A3)

*Created: 2026-08-15. Purpose: real, captured evidence of every documented
endpoint called with a real generated API key — or an explicit BLOCKED status.
Per the launch-execution prompt's hard constraints: **no simulated or
fabricated results are ever recorded here.***

---

## Status: BLOCKED — no API-Business subscription can be created

Checked `2026-08-15` in the build environment:

| Dependency | Status |
|---|---|
| `STRIPE_SECRET_KEY` (test mode) | ❌ not set — required to create an `api_business` subscription |
| `STRIPE_WEBHOOK_SECRET` | ❌ not set — required to process the subscription webhook |
| `STATLAS_DATASET_MODE` | `fixture-demo` (BLK-01) — responses would validate against fixtures, not production data |

**BLOCKED — API tier access requires an active `api_business` subscription,
which requires Stripe test-mode credentials (see
`docs/billing/live-verification-log.md`). Founder action: set the Stripe test
keys, create the API Business price (€49/month, `docs/billing/pricing-config.md`),
subscribe, then generate an API key.**

Why this is a hard block, not a preference: rate limits are plan-driven in
`app/api_keys.py` — free/pro plans have `api_rate_limit_per_minute: 0`, which
produces an explicit **403 with upgrade copy** (`"The public API is not
included in your current plan…"`). There is deliberately no back door: the
only way to exercise the 200-series behavior is a real API-Business
subscription.

---

## Test plan — executes verbatim once the block clears

### Endpoint inventory (from the live OpenAPI spec at `/api-docs`)

Key management (session-authenticated, dashboard):
1. `POST /api/v1/keys` `{name}` → 201, returns the **raw key once** (one-time
   reveal — capture it; it is not retrievable again)
2. `GET /api/v1/keys` → key list with **prefixes only** (never full keys)
3. `POST /api/v1/keys/{key_id}/rotate` → new raw key, old one dead
4. `DELETE /api/v1/keys/{key_id}` → `{ok: true}`, key immediately 401s

Rate-limited public reads (Bearer `<key>`):
5. `GET /api/v1/public/players/search?q=<name>` → results with disambiguating
   context
6. `GET /api/v1/public/players/{player_id}/percentiles` → profile + percentiles;
   unknown id → 404
7. `GET /api/v1/public/leaderboard?metric=<id>&league=<slug>&position=<group>&limit=<n>`
   - missing `league` → 400 with the actionable message
   - `limit=0` → 422 (`ge=1`), `limit=9999` → 422 (`le=100`), bad metric → 400
   - valid call → ranked rows

### Checks per endpoint (all with captured HTTP status + body)

- **Rate-limit headers present and accurate** on every read:
  `X-RateLimit-Limit` (120 for api_business), `X-RateLimit-Remaining`,
  `X-RateLimit-Window` (60s).
- **429 actually enforced:** fire 121 rapid requests at one endpoint; assert
  the 121st returns 429 with the stated limit, not a silent success. Verify
  the window resets the counter.
- **401s:** revoked key → 401; garbage token → 401; no header → 401.
- **Schema conformance:** every response body validates against the OpenAPI
  spec (the `/api-docs` page is generated from the implementation, so drift
  here would indicate a real bug).

### Result log format

```
## <date> — <test id>
- Endpoint: GET /api/v1/public/leaderboard?metric=…&league=…
- HTTP: 200
- Headers: X-RateLimit-Limit: 120, X-RateLimit-Remaining: 119, X-RateLimit-Window: 60s
- Body: <captured response>
```

*Never write PASS without captured responses.*
