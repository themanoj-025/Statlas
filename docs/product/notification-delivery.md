# Notification delivery — design notes

*Phase 10 (Part D). Covers the provider decision, preference-compliance
rules, digest behavior, and one-click unsubscribe mechanics.*

## Provider: Resend

Statlas's first outbound-email feature. Sender reputation established here
affects all future mail (including Phase 4 billing emails), so the choice
prioritized deliverability:

- **Resend** — developer-first transactional email API with a strong
  deliverability reputation and first-class support for RFC 8058
  `List-Unsubscribe` (genuine one-click unsubscribe, required by Part D1).
- Simple JSON HTTP API (`POST https://api.resend.com/emails`) — no SMTP
  plumbing, fits the existing `requests` dependency.
- Key-gated exactly like the Phase 4 assistant and Phase 9 reports: with
  `RESEND_API_KEY` unset, delivery reports an honest "not configured" state
  and alerts stay in-app; delivery never fails silently.

## Preference compliance (the non-negotiable bar)

Every delivery path checks, in order:

1. `notification_preferences.email_enabled` — global email off = no email.
2. `alert_type_preferences[alert_type]` — per-trigger-type opt-out.
3. `digest_frequency` — `immediate` users get per-alert email; `daily_digest`
   / `weekly_digest` users get batched digests only, never per-alert email.

In-app alerts (the `watch_alerts` rows) are recorded regardless — preferences
govern the outbound channel, never the data.

This is tested as rigorously as an authorization check: `test_preference_
compliance` generates a trigger for an opted-out user and asserts no email is
sent.

## Digests

- `daily_digest` sends one email per day, `weekly_digest` one per Monday
  (UTC), each batching every undelivered alert for that user.
- Alerts are marked `delivered_at` only after the digest email is sent, so a
  user switching frequency never loses an alert between modes.

## One-click unsubscribe

- Every email carries `List-Unsubscribe: <signed-url>` +
  `List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers and a footer
  link to the same URL.
- The URL is HMAC-signed (`ALERT_SIGNING_SECRET`) and includes the user's
  stored `unsubscribe_token`; the sessionless endpoint validates both before
  setting `email_enabled = False`.
- Token rotation (via the API) invalidates old email links — a reused link
  gets an honest "already used or replaced" response.
- `ALERT_SIGNING_SECRET` must be set in production; dev falls back to a
  per-process random value (links break on restart — acceptable for dev).
