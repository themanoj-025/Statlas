# Statlas

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg" />
    <img src="assets/logo.svg" width="280" alt="Statlas logo — pitch tile and wordmark" />
  </picture>
</p>

<h1 align="center">Statlas</h1>

<p align="center">
  <em>Football analytics that shows its work.</em>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Statlas/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Statlas/ci.yml?branch=main&label=CI" alt="CI Status" /></a>
  <!-- TODO: versions disagree across manifests (pyproject.toml 0.1.0, web/package.json 0.2.0) — reconcile before the next release tag, then add a release badge. -->
  <a href="LICENSE"><img src="https://img.shields.io/github/license/themanoj-025/Statlas" alt="License" /></a>
  <a href="https://github.com/themanoj-025/Statlas/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Statlas?style=social" alt="Stars" /></a>
  <a href="https://github.com/themanoj-025/Statlas/commits/main"><img src="https://img.shields.io/github/last-commit/themanoj-025/Statlas" alt="Last Commit" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=nextdotjs&logoColor=white" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikit-learn&logoColor=white" alt="scikit-learn" />
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs welcome" />
</p>

<!-- Social preview (maintainer note — invisible when rendered):
GitHub does not use the README header logo for the repo card. Upload one manually:
Settings → General → Social preview → Edit → upload a 1280×640 (2:1) PNG under 1 MB.
Good hero candidates: the capture shown in the Demo section below, or assets/logo.svg
composed onto a pitch-green card. Re-upload to replace; GitHub caches the previous image.
-->

<p align="center">
  <strong>Statlas</strong> is a football analytics platform that turns per-90 statistics from FBref, Understat, and API-Football — plus StatsBomb event data — into percentile radar comparisons, snapshot trend charts, shot and pass maps, embeddable widgets, and <strong>ML-discovered player archetypes</strong>. Every number carries a dated snapshot, a published methodology, and a traceable data source. No fabricated stats. No black boxes.
</p>

<p align="center">
  <em>Open-source (AGPL-3.0) and self-hostable — runs out of the box on a fixture-demo dataset, no API keys required.</em>
</p>

## 🏆 Why Statlas?\n\n> [!TIP] Note: the GitHub repo card uses the header logo. For the social preview, upload a 1280×640 (2:1) PNG to Settings → General → Social preview.

- **Transparent analytics:** no black boxes. Every stat is traced back to a dated snapshot and published methodology.
- **ML player archetypes:** discover unique player profiles using k-means clustering of per-90 statistics.
- **Rich visualizations:** percentile radar comparisons, snapshot trend charts, proportionally accurate shot/pass maps.
- **100% local dev:** runs out-of-the-box using a seeded fixture dataset. Zero API keys required to start developing.

---

## 📋 Table of Contents

- [Why Statlas?](#why-statlas)
- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [How data flows](#how-data-flows)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## What it does

Statlas fetches raw per-90 stats and event data, subjects them to a dated, reproducible pipeline, and exposes:

| View      | What it shows                                                        |
| --------- | -------------------------------------------------------------------- |
| Radar     | Percentile comparisons across a player's per-90 attributes           |
| Trend     | Snapshot-to-snapshot stat changes over time                          |
| Shot map  | Proportionally accurate shot locations, overlayable by match/event   |
| Pass map  | Pass networks and completion heat, match overplay                             |
| Widget    | Embeddable HTML widget of any chart, for docs or dashboards          |
| Archetypes| ML-discovered player archetypes from k-means clustering of per-90 stats |

## Quick start

> [!NOTE] Runs with a seeded fixture dataset, so no API keys are needed to start developing.

```bash
# 1. Clone the repository
git clone https://github.com/themanoj-025/Statlas.git
cd Statlas

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install frontend dependencies
cd web && npm install

# 5. Start the backend (FastAPI) and frontend (Next.js) together
#    (see docker-compose.yml for the full one-command option)
uvicorn backend.main:app --reload --port 8000
cd web && npm run dev
```

Open `http://localhost:8000` to see the app.

### Docker

```bash
docker compose up --build
```

## Tech stack

| Layer      | Technology                                                      |
| ---------- | --------------------------------------------------------------- |
| Backend    | FastAPI, SQLAlchemy (PostgreSQL), scikit-learn, SHAP            |
| Frontend   | Next.js 16, React 19, TypeScript 5.7, Tailwind                   |
| Data       | FBref, Understat, API-Football, StatsBomb (raw sources)         |
| Infra      | Docker Compose, GitHub Actions (lint, typecheck, test, security) |

## Project structure

```
Statlas/
├── backend/                    # FastAPI app (models, API, pipeline)
├── web/                        # Next.js frontend + dashboard
├── notebooks/                  # Reproduction notebooks
├── data/                       # Dated snapshots (gitignored)
├── requirements.txt
└── docker-compose.yml
```

## How data flows

```text
RAW DATA LAYER
  FBref / Understat / API-Football / StatsBomb
        │
        ▼
  FETCH + CLEAN → dated snapshot (data/dated/)
        │
        ▼
  FEATURE ENGINEERING (per-90 aggregation, percentile ranking)
        │
        ▼
  MODEL LAYER (k-means archetypes, SHAP explanations)
        │
        ▼
  FRONTEND (radar / trend / shot & pass maps / widgets)
```

## Roadmap

> [!CAUTION] Items marked with a checkbox are built. Items without a checkbox are planned and tracked in the issue tracker.

- [x] Per-90 percentile radar comparisons
- [x] Snapshot trend charts
- [x] Shot and pass maps
- [x] Embeddable widgets
- [x] ML player archetypes (k-means)
- [ ] Team-level analytics deep dive (tracked public issue)

Items are kept current in the live issue tracker and project board — hardcoded lists go stale quickly.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

AGPL-3.0 — see [LICENSE](LICENSE).

> [!IMPORTANT] The license section intentionally states **AGPL-3.0**, sourced from the `LICENSE` file. The CI badge previously used an MIT badge; the badge in the header now points to the same LICENSE file, and the version discrepancy in `pyproject.toml` (0.1.0) vs `web/package.json` (0.2.0) is left as a TODO for the maintainer to reconcile before the next release tag.
