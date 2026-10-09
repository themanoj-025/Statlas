# Authentication Policy

## Password Requirements

- Minimum 8 characters, maximum 200 characters
- No additional complexity requirements enforced (the Constitution's "unglamorous by design"
  philosophy applies to password rules too — mandatory special characters reduce security
  by encouraging predictable substitutions; length is the primary strength indicator)
- Passwords are hashed with PBKDF2-HMAC-SHA256, 600,000 iterations, random 16-byte salt
- Hash format: `{iterations}${salt_hex}${hash_hex}`

## Password Reset

- User requests reset via `POST /api/v1/auth/password-reset/request` with their email
- Response is always 200 with the same message regardless of whether the email exists
  (prevents account enumeration)
- A single-use, time-limited token (60-minute expiry) is created and hashed before storage
- An email is sent with a link to `/reset-password?token=...`
- User submits new password via `POST /api/v1/auth/password-reset/confirm`
- Token is marked as used after successful reset; expired tokens are rejected

## Email Verification

- Sent on registration automatically
- User can request re-verification via `POST /api/v1/auth/verify-email/request`
- Single-use token, 24-hour expiry
- Email verification is a soft nudge — unverified users retain full access
  (the product works without verification; it's a deliverability/trust signal,
  not a gating mechanism)

## Login Rate Limiting

- After 5 failed login attempts within 10 minutes for the same email, the account
  is temporarily locked for 15 minutes
- The lockout response returns 429 with a retry-after header
- Successful login resets the failure counter
- Lockout state is tracked in-memory (sufficient for single-server deployments;
  Redis-backed for horizontal scaling when needed)

## Session Management

- Sessions are 30-day rolling (configurable via `SESSION_TTL_HOURS`)
- Session tokens are SHA-256 hashed before storage; raw value is never persisted
- Logout revokes the session and clears the cookie
- Multiple concurrent sessions are allowed (device diversity)

## Account Deletion

- User requests deletion via the account settings page
- Account enters `pending_deletion` status with a 30-day grace period
- During grace period, user can cancel deletion by logging in
- After 30 days, account and all associated data are permanently deleted
- Downstream data (shortlists, saved searches, reports, watches) is deleted with the account
