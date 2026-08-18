# Account System Audit — Phase 12 Pre-Work

*Audited: 2026-08-18. This document was written BEFORE any Phase 12 schema or application
code was changed, per the Constitution's "never silently swallow a gap" discipline.*

## A1. Existing Auth/User Infrastructure

### Users table

The `users` table exists as a proper identity table independent of billing:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `email` | VARCHAR(320) UNIQUE | Case-insensitive via `.lower()` on insert |
| `password_hash` | VARCHAR(255) | PBKDF2-HMAC-SHA256, 600k iterations, random 16-byte salt |
| `plan` | VARCHAR(12) | "free" or "pro" — denormalized from subscriptions for fast reads |
| `created_at` | DATETIME | CURRENT_TIMESTAMP default |

**Verdict:** This is a real, independent user identity table. Email + password hash exist.
"User" is NOT inferred from Stripe customer ID — it has its own login mechanism.

### Session mechanism

`session_tokens` table provides real session-based auth:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK→users.id | |
| `token_hash` | VARCHAR(64) | SHA-256 of raw token — raw value NEVER stored |
| `created_at` | DATETIME | |
| `expires_at` | DATETIME | 30-day TTL (configurable via settings) |
| `revoked_at` | DATETIME nullable | Set on logout |

Cookie: `statlas_session`, HttpOnly, SameSite=Lax, secure flag for HTTPS deployments.

**Verdict:** Real, secure session management exists. Login, logout, session lookup all work.

### Auth endpoints

All in `app/api/billing_views.py`:

- `POST /api/v1/auth/register` — email/password registration (duplicate-email 409)
- `POST /api/v1/auth/login` — email/password login (generic "Incorrect email or password" — no enumeration leak)
- `POST /api/v1/auth/logout` — revoke session + clear cookie
- `GET /api/v1/auth/me` — current user + has_pro

### Downstream FK references (all point to users.id)

| Table | FK column | Target |
|-------|-----------|--------|
| `shortlists` | `user_id` | `users.id` |
| `saved_searches` | `user_id` | `users.id` |
| `reports` | `user_id` | `users.id` |
| `watches` | `user_id` | `users.id` |
| `notification_preferences` | `user_id` | `users.id` |
| `assistant_quotas` | `user_id` | `users.id` |

**Verdict:** Every Phase 7-10 table correctly references the canonical `users.id`.
No migration of downstream FKs is needed.

## A2. Migration Strategy

**Path: Minimal gap (Path 1)**

The `users` table with real identity already exists. Phase 4 built registration, login,
logout, and session management. All downstream tables reference `users.id` correctly.

**What's missing (Phase 12 adds these, purely additive):**

1. **Password reset** — no forgot-password flow exists
2. **Email verification** — no email verification at signup
3. **Login rate limiting** — no brute-force protection beyond generic error message
4. **Profile fields** — no `display_name`, `timezone`, `locale`, `email_verified_at`,
   `account_status` on the users table
5. **Profile/preferences UI** — the `/account` page exists but only shows billing/quota,
   not profile editing, password change, or notification preferences integration
6. **Account deletion** — no deletion flow exists
7. **Auth policy documentation** — no `docs/engineering/auth-policy.md`

**No breaking migration needed.** All additions are additive columns/tables.
Existing users retain their accounts and all data unchanged.

## A3. Audit Complete

This audit was written before any Phase 12 schema or application code was changed.
The findings are based on direct inspection of `app/models.py`, `app/auth.py`,
`app/api/billing_views.py`, `app/schema.sql`, and the dev database.
