<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg" />
    <img src="assets/logo.svg" width="280" alt="Statlas logo — pitch tile and wordmark" />
  </picture>
</p>

<h1 align="center">Statlas</h1>

<p align="center">
  <strong>Football analytics that shows its work: transparent metrics, percentile radar profiles, shot maps, and ML-discovered player archetypes.</strong>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Statlas/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Statlas/ci.yml?branch=main&label=CI" alt="CI Status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square" alt="License AGPL-3.0" /></a>
  <a href="https://github.com/themanoj-025/Statlas/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Statlas?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/themanoj-025/Statlas/issues"><img src="https://img.shields.io/github/issues/themanoj-025/Statlas?style=flat-square" alt="GitHub Issues" /></a>
  <a href="https://github.com/themanoj-025/Statlas/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome" /></a>
</p>

<!-- TODO: versions disagree across manifests (pyproject.toml 0.1.0, web/package.json 0.2.0) — reconcile before the next release tag. -->

---

## Overview

Statlas is an open-source football analytics and intelligence platform that transforms raw match events and per-90 metrics (from sources like StatsBomb, FBref, and Understat) into insightful visualizations. Features include percentile radar charts, longitudinal performance trendlines, spatial shot and pass networks, embeddable visual widgets, and unsupervised k-means player archetype discovery.

Every calculated metric is linked to an immutable timestamped snapshot and transparent methodological calculation. The platform runs out of the box with zero external API dependencies using seeded demonstration fixtures.

---

## Table of Contents

- [Key Features](#key-features)
- [Analytics Visualizations](#analytics-visualizations)
- [Tech Stack](#tech-stack)
- [Architecture & Data Flow](#architecture--data-flow)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Quick Start](#installation--quick-start)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Key Features

- **Transparent Statistical Provenance**: Eliminates opaque rating scores; all metrics carry source attribution, computation logs, and timestamped snapshot IDs.
- **Unsupervised Player Archetypes**: Leverages k-means clustering over standardized per-90 features to uncover latent stylistic roles across leagues.
- **Geospatial Shot & Pass Visualizations**: Generates coordinate-accurate pitch representations depicting shot trajectories, pass networks, and zonal pressure maps.
- **Embeddable Chart Widgets**: Modular HTML export capabilities for publishing charts directly into third-party dashboards or editorial articles.
- **Full Offline Developer Experience**: Ships with comprehensive seed fixture databases, enabling immediate local development with zero third-party API subscriptions.

---

## Analytics Visualizations

| Visualization | Analytical Purpose |
| :--- | :--- |
| **Percentile Radar** | Multidimensional evaluation comparing player performance against position-specific league distributions |
| **Longitudinal Trends** | Tracks evolution of key underlying indicators across match snapshots |
| **Spatial Shot Maps** | Visualizes shot coordinates with expected goals (xG) sizing and outcome indicators |
| **Passing Networks** | Displays team passing volume, passing heat, and progressive carrying lanes |
| **Player Archetypes** | Clusters footballers by tactical behavior (e.g., Deep-Lying Playmaker vs. Box-to-Box Engine) |

---

## Tech Stack

| Domain | Technology |
| :--- | :--- |
| **Backend Framework** | FastAPI 0.110+, SQLAlchemy 2.x, Pydantic v2 |
| **Frontend Dashboard** | Next.js 16, React 19, TypeScript 5.7, Tailwind CSS |
| **Machine Learning** | scikit-learn (k-means clustering), SHAP |
| **Database & Cache** | PostgreSQL / SQLite (`dev.db`), Redis |
| **Container & CI** | Docker Compose, GitHub Actions |

---

## Architecture & Data Flow

```text
       Raw Data Sources (StatsBomb, FBref, Understat)
                            │
                            ▼
              Data Ingestion & Cleaning Engine
              (Dated Snapshots in data/dated/)
                            │
                            ▼
               Feature Engineering Pipeline
       (Per-90 Normalization & Percentile Ranking)
                            │
                            ▼
               Machine Learning & Analytics
       (K-Means Archetypes & Tactical Aggregations)
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
     FastAPI Backend               Next.js Web Frontend
  (app.api.main:app, Port 8000)      (web/, Port 3000)
```

---

## Project Structure

```text
Statlas/
├── app/                    # FastAPI backend package
│   ├── analytics/          # Statistical computation modules
│   ├── api/                # API route controllers and endpoint schemas
│   │   └── main.py         # Primary FastAPI application instance
│   ├── compute/            # Archetype clustering and data transformation
│   ├── models/             # SQLAlchemy ORM models
│   └── sources/            # Data source adapters (StatsBomb, etc.)
├── web/                    # Next.js 16 frontend application
│   ├── app/                # App router pages and views
│   ├── components/         # Radar, pitch, and chart visual components
│   └── package.json        # Frontend dependencies
├── data/                   # Seed database and cached snapshots
├── tests/                  # Pytest backend test suite
├── Dockerfile              # Multi-stage production container build
├── docker-compose.yml      # Multi-service local environment
├── pyproject.toml          # Python build backend and Ruff configuration
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## Prerequisites

- **Python**: `>= 3.10`
- **Node.js**: `>= 18.0`
- **Docker**: Optional, for multi-service compose orchestration

---

## Installation & Quick Start

### 1. Clone Repository & Setup Backend

```bash
# Clone the repository
git clone https://github.com/themanoj-025/Statlas.git
cd Statlas

# Setup Python virtual environment
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Start FastAPI backend
uvicorn app.api.main:app --reload --port 8000
```

### 2. Setup & Run Frontend

In a separate terminal:

```bash
cd web
npm install
npm run dev
```

*Open http://localhost:3000 to view the Next.js web application.*  
*Backend API docs available at http://localhost:8000/docs.*

---

## Testing

```bash
# Execute backend test suite
pytest tests/ -v
```

---

## Docker Deployment

```bash
# Start backend, web frontend, and database services
docker compose up --build -d
```

---

## Roadmap

- [x] Per-90 percentile radar visualization
- [x] Longitudinal metric trend charts
- [x] Coordinate-accurate shot and pass maps
- [x] Unsupervised k-means player archetype discovery
- [x] Seeded offline fixture dataset
- [ ] Team-level possession and defensive structure analytics <!-- TODO: Track via GitHub issue -->
- [ ] Exportable automated scouting PDF reports <!-- TODO: Track via GitHub issue -->

---

## Contributing

Contributions are welcomed! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).

---

## Support

- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/themanoj-025/Statlas/issues)
- 💡 **Discussions & Feedback**: [GitHub Pull Requests](https://github.com/themanoj-025/Statlas/pulls)
