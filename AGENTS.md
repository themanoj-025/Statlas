# AGENTS.md — Statlas

> Canonical project instructions. Pointers like `CLAUDE.md` or
> `.github/copilot-instructions.md` should say "See AGENTS.md".

---

## Project overview

**Statlas** — a statistics dashboard and reporting platform. Core
components:

- **API** — FastAPI service for statistics queries.
- **Dashboard** — Streamlit app for exploring statistics.
- **Web / App** — frontend consuming the API.
- **Model** — statistics computation backend.

Stack: Python 3.11+ · FastAPI · Streamlit.

---

## Exact commands

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Lint / typecheck / test
make lint
pre-commit run --all-files
python -m mypy . --ignore-missing-imports
python -m pytest tests/ -v --cov=. --cov-fail-under=70

# Run
uvicorn api.main:app --reload
streamlit run dashboard/app.py
```

---

## Folder map

| Path | Purpose |
|------|---------|
| `api/` | FastAPI application (routes, services) |
| `dashboard/` | Streamlit dashboard |
| `model/` | Statistics computation |
| `tests/` | pytest suite |
| `.github/workflows/` | CI (ruff, mypy, pytest, gitleaks, trivy) |

## Do / don't

- **Do** keep the statistics service behind a stable interface.
- **Do not** commit `.env` files.
- **Do not** commit raw underlying datasets (PII or licensed data).

## Security rules

- No secrets in the repository; `gitleaks` CI gate gates on hits.
- Underlying data must be anonymized before any file leaves the sandbox.

## AI-assistance convention

Commits authored by AI must carry the trailer:

```text
AI-Assisted: yes | no | partial
```

See `.gitmessage` for the template. Do not rewrite historic commits
retroactively.
