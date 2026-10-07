# 📜 Transcripts Directory Policy

This directory is the sanitized, AI-conversation transcript archive for
Statlas. It exists so the project can point future tooling at the
records without cluttering the repo with one-off exports.

## Contents

| Item | Purpose |
|------|---------|
| `README.md` | This policy file |
| `*.json` / `*.md` / `*.txt` | Sanitized conversation exports, organized by date/label |

## Sanitization rules

- **Never** commit real credentials, tokens, API keys, or secrets.
- Replace internal hostnames, private URLs, and email addresses with
  clearly-marked placeholders (`***REDACTED***`).
- Preserve the conversation structure (user turns, assistant turns, tool
  calls) so the record remains useful for review.
- Keep filenames date-labelled (`YYYY-MM-DD_<short-desc>`) for sortability.

## Policy

- Transcripts are archived, not edited after the fact, unless a redaction
  check fails.
- Large transcripts may live outside the repo and be referenced by a
  pointer file (`pointer.md`) that contains the source location and a
  checksum.
- `ai-provenance.json` and `AI_DISCLOSURE.md` are the machine- and
  human-readable summaries of the same activity; transcripts are the
  underlying evidence.

## Last Updated

2026-10-06 · Maintained by `themanoj-025 <code.me.025@gmail.com>`
