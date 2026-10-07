# 🔬 AI Tools & Provenance

This directory holds the AI-assistance records for Statlas: disclosures,
prompt archives, provenance ledgers, and sanitized conversation transcripts.

---

## Contents

| File | Purpose |
|------|---------|
| `README.md` | This directory index |
| `AI_DISCLOSURE.md` | What AI tools were used and what they did |
| `ai-provenance.json` | Structured machine-readable provenance (schema 1.0) |
| `PROVENANCE.md` | Human-readable milestone ledger with commit hashes |
| `PROMPTS.md` | Sanitized prompt archive (date-labelled) |
| `transcripts/README.md` | Transcript directory policy |
| `transcripts/` | Sanitized conversation exports (see `transcripts/README.md`) |

---

## How to use

- **Verify** the files are tracked: `git ls-files "docs/ai/"` and
  `git ls-files "ai-provenance.json" "AI_DISCLOSURE.md"`.
- **Validate** the JSON: `python -m json.tool ai-provenance.json`.
- **Confirm** provenance pathways are not ignored:
  `git check-ignore -v AI_DISCLOSURE.md ai-provenance.json docs/ai/ 2>&1`.
- **Add a new entry** (IDs must end with `AI-Assisted: yes` in the body,
  per `.gitmessage`).

---

## Redaction policy

All files in this directory must not contain real credentials, tokens,
internal hostnames, email addresses, or private URLs. Where such data
appeared in a conversation, replace it with clearly-marked placeholders
(`***REDACTED***`).

---

## Last Updated

2026-10-06 · Maintained by `themanoj-025 <code.me.025@gmail.com>`
