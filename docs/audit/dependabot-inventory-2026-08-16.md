# Dependabot PR Inventory — 2026-08-16

**Total open Dependabot PRs: 179** across 16 repos.

Method: `gh pr list --author app/dependabot --state open` per repo; per-PR CI read from the latest workflow run on the PR head commit. Merge decisions follow the master dependabot policy: never merge on red/stale CI, always verify locally before merge.

## Per-repo summary

| Repo | PRs | CI green | CI fail/skip | Base CI | Notes |
|---|---|---|---|---|---|
| AI-Telegram-News-Bot | 2 | 2 | 0 | green |  |
| AegisAI | 15 | 4 | 11 | BROKEN | CI-deferred (broken base) |
| Book-Tale | 3 | 2 | 1 | BROKEN | CI-deferred (broken base) |
| Credit Card Fraud Detection | 19 | 14 | 5 | BROKEN | CI-deferred (broken base) |
| Dabba | 17 | 8 | 9 | green |  |
| Emotion-Lens | 3 | 2 | 1 | green |  |
| Institute-Management-System | 23 | 15 | 8 | green |  |
| Match-Mind | 1 | 1 | 0 | green |  |
| Next-Gen-Reco | 9 | 8 | 1 | BROKEN | CI-deferred (broken base) |
| Price-My-Car | 12 | 3 | 9 | BROKEN | CI-deferred (broken base) |
| Smart-Spam-Detector | 4 | 2 | 2 | green |  |
| Statlas | 10 | 4 | 6 | green |  |
| Tamasha | 18 | 13 | 5 | BROKEN | CI-deferred (broken base) |
| UNION-BANK- | 10 | 0 | 10 | green |  |
| Veridoc | 27 | 21 | 6 | green | 9 needs-human-review |
| finsight-agent | 6 | 6 | 0 | green |  |

## Classification

- **MERGE CANDIDATES (green CI + mergeable): 97** - qualify for local-verification-then-merge.
- **CI-DEFERRED (red/skipped CI or broken base): 73** - cannot merge until base/PR CI is fixed.
- **NEEDS HUMAN REVIEW (labeled): 9** - held.
- **OTHER/UNKNOWN: 0**

### Merge candidates (97)

| Repo | PR | Title |
|---|---|---|
| AI-Telegram-News-Bot | #1 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| AI-Telegram-News-Bot | #2 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| AegisAI | #7 | chore(deps)(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| AegisAI | #8 | deps(deps): update tenacity requirement from >=9.0.0 to >=9.1.4 |
| AegisAI | #11 | deps(deps): update anthropic requirement from >=0.45.0 to >=0.121.0 |
| AegisAI | #12 | deps(deps): update fastapi requirement from >=0.115.0 to >=0.141.1 |
| Book-Tale | #6 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| Book-Tale | #7 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Credit Card Fraud Detection | #1 | deps(deps): update lightgbm requirement from <4.0.0,>=3.3.0 to >=4.7.0,<5.0.0 |
| Credit Card Fraud Detection | #2 | deps(deps): update pandas requirement from <3.0.0,>=2.1.0 to >=3.0.5,<4.0.0 |
| Credit Card Fraud Detection | #3 | deps(deps): update pre-commit requirement from <4.0.0,>=3.0.0 to >=4.6.2,<5.0.0 |
| Credit Card Fraud Detection | #4 | deps(deps): update pydantic requirement from >=2.0.0 to >=2.13.4 |
| Credit Card Fraud Detection | #6 | deps(deps): update fastapi requirement from <1.0.0,>=0.116.0 to >=0.141.1,<1.0.0 |
| Credit Card Fraud Detection | #7 | deps(deps): update pytest-xdist requirement from <4.0.0,>=3.3.0 to >=3.8.0,<4.0.0 |
| Credit Card Fraud Detection | #10 | deps(deps): update evidently requirement from <1.0.0,>=0.3.0 to >=0.7.21,<1.0.0 |
| Credit Card Fraud Detection | #11 | chore(deps)(deps): bump actions/cache from 4 to 6 |
| Credit Card Fraud Detection | #13 | chore(deps)(deps): bump https://github.com/PyCQA/isort from 5.13.2 to 8.0.1 |
| Credit Card Fraud Detection | #14 | chore(deps)(deps): bump docker/metadata-action from 5 to 6 |
| Credit Card Fraud Detection | #16 | chore(deps)(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| Credit Card Fraud Detection | #17 | chore(deps)(deps): bump https://github.com/psf/black from 24.10.0 to 26.5.1 |
| Credit Card Fraud Detection | #18 | chore(deps)(deps): bump dependabot/fetch-metadata from 2 to 3 |
| Credit Card Fraud Detection | #20 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Dabba | #1 | chore(deps)(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| Dabba | #6 | deps(deps): update pydantic requirement from <3.0,>=2.5 to >=2.13.4,<3.0 |
| Dabba | #8 | deps(deps): update sqlalchemy requirement from <3.0,>=2.0 to >=2.0.52,<3.0 |
| Dabba | #9 | deps(deps): update slowapi requirement from <1.0,>=0.1.9 to >=0.1.10,<1.0 |
| Dabba | #10 | deps(deps): update pyjwt requirement from <3.0,>=2.8 to >=2.13.0,<3.0 |
| Dabba | #11 | deps(deps): update prometheus-client requirement from <1.0,>=0.19 to >=0.26.0,<1.0 |
| Dabba | #14 | deps(deps): update faiss-cpu requirement from <2.0,>=1.7 to >=1.15.0,<2.0 |
| Dabba | #16 | chore(deps)(deps): bump https://github.com/pycqa/isort from 5.13.2 to 8.0.1 |
| Emotion-Lens | #2 | deps(deps): bump pillow from 10.1.0 to 12.3.0 |
| Emotion-Lens | #4 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| Institute-Management-System | #1 | deps(deps-dev): bump @vitejs/plugin-react from 4.7.0 to 6.0.5 in /web |
| Institute-Management-System | #3 | deps(deps-dev): bump vite from 6.4.3 to 8.2.1 in /web |
| Institute-Management-System | #4 | deps(deps-dev): bump jsdom from 29.1.1 to 30.0.1 in /web |
| Institute-Management-System | #6 | deps(deps): update xgboost requirement from >=2.0.0 to >=3.4.0 |
| Institute-Management-System | #7 | deps(deps): update alembic requirement from >=1.13.0 to >=1.19.1 |
| Institute-Management-System | #11 | deps(deps): update celery requirement from >=5.4.0 to >=5.6.3 |
| Institute-Management-System | #12 | deps(deps): update opentelemetry-instrumentation-fastapi requirement from >=0.46b0 to >=0.65b0 |
| Institute-Management-System | #13 | deps(deps): update opentelemetry-exporter-otlp requirement from >=1.25.0 to >=1.44.0 |
| Institute-Management-System | #16 | ci(deps): bump dependabot/fetch-metadata from 2 to 3 |
| Institute-Management-System | #17 | ci(deps): bump docker/setup-buildx-action from 3 to 4 |
| Institute-Management-System | #18 | ci(deps): bump docker/login-action from 3 to 4 |
| Institute-Management-System | #21 | chore(deps)(deps): bump https://github.com/pycqa/isort from 5.13.2 to 8.0.1 |
| Institute-Management-System | #22 | chore(deps)(deps): bump https://github.com/pre-commit/mirrors-mypy from v1.15.0 to 2.3.0 |
| Institute-Management-System | #24 | chore(deps)(deps): bump https://github.com/psf/black from 24.10.0 to 26.5.1 |
| Institute-Management-System | #25 | chore(deps)(deps): bump pydantic from 2.0.0 to 2.13.4 |
| Match-Mind | #1 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Next-Gen-Reco | #1 | deps(deps): update pandas requirement from >=1.5.0 to >=3.0.5 |
| Next-Gen-Reco | #2 | deps(deps): update scikit-learn requirement from >=1.3.0 to >=1.9.0 |
| Next-Gen-Reco | #3 | deps(deps): update joblib requirement from >=1.2.0 to >=1.5.3 |
| Next-Gen-Reco | #4 | deps(deps): update numpy requirement from >=1.24.0 to >=2.5.2 |
| Next-Gen-Reco | #5 | deps(deps): update pyarrow requirement from >=10.0.0 to >=25.0.1 |
| Next-Gen-Reco | #6 | deps(deps): update streamlit requirement from >=1.60.0 to >=1.61.1 |
| Next-Gen-Reco | #7 | deps(deps): update requests requirement from >=2.28.0 to >=2.34.2 |
| Next-Gen-Reco | #9 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| Price-My-Car | #9 | deps(deps): update bcrypt requirement from >=4.0.0 to >=5.0.0 |
| Price-My-Car | #11 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| Price-My-Car | #12 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Smart-Spam-Detector | #3 | chore(deps)(deps): bump https://github.com/astral-sh/ruff-pre-commit from v0.9.10 to 0.16.2 |
| Smart-Spam-Detector | #4 | chore(deps)(deps): bump https://github.com/pre-commit/mirrors-mypy from v1.15.0 to 2.3.0 |
| Statlas | #6 | chore(deps-dev): bump typescript from 5.9.3 to 7.0.2 in /web |
| Statlas | #8 | chore(deps-dev): bump @types/node from 22.20.1 to 26.2.0 in /web |
| Statlas | #9 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Statlas | #10 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| Tamasha | #4 | chore(deps)(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| Tamasha | #5 | deps(deps): update uvicorn requirement from <1.0,>=0.24 to >=0.52.1,<1.0 |
| Tamasha | #6 | chore(deps)(deps): bump dependabot/fetch-metadata from 2 to 3 |
| Tamasha | #7 | deps(deps): update isort requirement from <6.0,>=5.12 to >=8.0.1,<9.0 |
| Tamasha | #8 | deps(deps): update pytest requirement from <8.0,>=7.4 to >=9.1.1,<10.0 |
| Tamasha | #9 | deps(deps): update pydantic-settings requirement from <3.0,>=2.0 to >=2.15.0,<3.0 |
| Tamasha | #11 | deps(deps-dev): update setuptools requirement from >=68.0 to >=84.0.0 |
| Tamasha | #12 | deps(deps): update pydantic requirement from <3.0,>=2.0 to >=2.13.4,<3.0 |
| Tamasha | #13 | deps(deps): update streamlit requirement from <2.0,>=1.28 to >=1.61.1,<2.0 |
| Tamasha | #14 | deps(deps): update fastapi requirement from <1.0,>=0.116 to >=0.141.1,<1.0 |
| Tamasha | #15 | deps(deps): update scipy requirement from <2.0,>=1.10 to >=1.15.3,<2.0 |
| Tamasha | #16 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v4.5.0 to 6.0.0 |
| Tamasha | #18 | chore(deps)(deps): bump https://github.com/PyCQA/isort from 5.12.0 to 8.0.1 |
| Veridoc | #5 | Bump actions/setup-node from 4 to 7 |
| Veridoc | #11 | chore(deps): bump pillow from 11.0.0 to 12.3.0 in /backend |
| Veridoc | #15 | chore(deps): bump structlog from 24.4.0 to 26.1.0 in /backend |
| Veridoc | #22 | chore(deps-dev): bump @types/node from 20.19.43 to 26.2.0 in /frontend |
| Veridoc | #23 | chore(deps): bump chromadb from 0.5.5 to 1.5.9 in /backend |
| Veridoc | #28 | chore(deps): bump pydantic-settings from 2.5.2 to 2.15.0 in /backend |
| Veridoc | #30 | chore(deps): bump sse-starlette from 2.1.0 to 3.4.8 in /backend |
| Veridoc | #31 | chore(deps): bump tailwind-merge from 2.6.1 to 3.6.0 in /frontend |
| Veridoc | #32 | chore(deps): bump alembic from 1.18.5 to 1.19.1 in /backend |
| Veridoc | #33 | chore(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| Veridoc | #34 | chore(deps): bump actions/checkout from 4 to 7 |
| Veridoc | #35 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| Veridoc | #36 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |
| finsight-agent | #1 | chore(deps): bump actions/checkout from 4 to 7 |
| finsight-agent | #2 | chore(deps): bump actions/setup-python from 5 to 7 |
| finsight-agent | #3 | chore(deps): bump gitleaks/gitleaks-action from 2 to 3 |
| finsight-agent | #4 | chore(deps): bump dependabot/fetch-metadata from 2 to 3 |
| finsight-agent | #5 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 |
| finsight-agent | #6 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 |

### CI-deferred (73)

| Repo | PR | Title | CI |
|---|---|---|---|
| AegisAI | #16 | deps(deps): update rq requirement from <2.0,>=1.16.0 to >=2.10.0,<3.0 | failure |
| AegisAI | #15 | deps(deps): update redis requirement from >=5.2.0 to >=8.1.0 | failure |
| AegisAI | #14 | deps(deps): update pyjwt requirement from >=2.10.0 to >=2.13.0 | failure |
| AegisAI | #13 | deps(deps): update pydantic-settings requirement from >=2.6.0 to >=2.15.0 | failure |
| AegisAI | #10 | deps(deps): update uvicorn requirement from >=0.32.0 to >=0.52.1 | failure |
| AegisAI | #9 | deps(deps): update python-dotenv requirement from >=1.0.0 to >=1.2.2 | failure |
| AegisAI | #6 | chore(deps)(deps): bump dependabot/fetch-metadata from 2 to 3 | failure |
| AegisAI | #5 | chore(deps)(deps): bump actions/setup-python from 5 to 7 | failure |
| AegisAI | #3 | chore(deps)(deps): bump actions/checkout from 4 to 7 | failure |
| AegisAI | #2 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 | failure |
| AegisAI | #1 | chore(deps)(deps): bump https://github.com/psf/black from 25.9.0 to 26.5.1 | failure |
| Book-Tale | #5 | deps(deps): update croniter requirement from >=2.0.0 to >=6.2.4 | skipped |
| Credit Card Fraud Detection | #19 | chore(deps)(deps): bump https://github.com/kynan/nbstripout from 0.8.1 to 0.9.1 | failure |
| Credit Card Fraud Detection | #12 | chore(deps)(deps): bump actions/setup-python from 5 to 7 | failure |
| Credit Card Fraud Detection | #9 | deps(deps): update umap-learn requirement from <1.0.0,>=0.5.3 to >=0.5.12,<1.0.0 | failure |
| Credit Card Fraud Detection | #8 | deps(deps): update isort requirement from <6.0.0,>=5.12.0 to >=8.0.1,<9.0.0 | failure |
| Credit Card Fraud Detection | #5 | deps(deps): update mlflow requirement from <3.0.0,>=2.3.0 to >=3.15.1,<4.0.0 | failure |
| Dabba | #19 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v4.5.0 to 6.0.0 | failure |
| Dabba | #18 | chore(deps)(deps): bump https://github.com/psf/black from 24.3.0 to 26.5.1 | failure |
| Dabba | #15 | deps(deps): update shap requirement from <1.0,>=0.43 to >=0.51.0,<1.0 | failure |
| Dabba | #13 | deps(deps): update redis requirement from <6.0,>=5.0 to >=8.1.0,<9.0 | failure |
| Dabba | #12 | deps(deps): update fastapi requirement from <1.0,>=0.104 to >=0.141.1,<1.0 | failure |
| Dabba | #5 | chore(deps)(deps): bump codecov/codecov-action from 4 to 7 | failure |
| Dabba | #4 | chore(deps)(deps): bump actions/checkout from 4 to 7 | failure |
| Dabba | #3 | deps(deps): update nltk requirement from <4.0,>=3.8 to >=3.10.2,<4.0 | failure |
| Dabba | #2 | chore(deps)(deps): bump actions/setup-python from 5 to 7 | failure |
| Emotion-Lens | #3 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 | failure |
| Institute-Management-System | #23 | chore(deps)(deps): bump sqlalchemy from 2.0.30 to 2.0.52 | failure |
| Institute-Management-System | #20 | ci(deps): bump actions/setup-node from 4 to 7 | failure |
| Institute-Management-System | #19 | ci(deps): bump actions/upload-artifact from 4 to 7 | failure |
| Institute-Management-System | #15 | deps(deps): update pytest requirement from >=9.0.3 to >=9.1.1 | failure |
| Institute-Management-System | #14 | deps(deps): update sqlalchemy requirement from >=2.0.51 to >=2.0.52 | failure |
| Institute-Management-System | #10 | deps(deps): bump openpyxl from 3.1.2 to 3.1.5 | failure |
| Institute-Management-System | #9 | deps(deps): bump reportlab from 4.0.7 to 5.0.0 | failure |
| Institute-Management-System | #8 | deps(deps): update opentelemetry-sdk requirement from >=1.25.0 to >=1.44.0 | failure |
| Next-Gen-Reco | #8 | chore(deps)(deps): bump https://github.com/pre-commit/pre-commit-hooks from v5.0.0 to 6.0.0 | failure |
| Price-My-Car | #10 | deps(deps): update seaborn requirement from >=0.12.0 to >=0.13.2 | failure |
| Price-My-Car | #8 | deps(deps): update jupyter requirement from >=1.0.0 to >=1.1.1 | failure |
| Price-My-Car | #7 | deps(deps): update scipy requirement from >=1.10.0 to >=1.18.0 | failure |
| Price-My-Car | #6 | deps(deps): update nbformat requirement from >=5.0.0 to >=5.11.0 | failure |
| Price-My-Car | #5 | deps(deps): update xgboost requirement from >=1.7.0 to >=3.4.0 | failure |
| Price-My-Car | #4 | deps(deps): update scikit-learn requirement from >=1.3.0 to >=1.9.0 | failure |
| Price-My-Car | #3 | deps(deps): update numpy requirement from >=2.5.1 to >=2.5.2 | failure |
| Price-My-Car | #2 | deps(deps): update streamlit requirement from >=1.60.0 to >=1.61.1 | failure |
| Price-My-Car | #1 | deps(deps): update setuptools requirement from >=78.1.1 to >=84.0.0 | failure |
| Smart-Spam-Detector | #2 | deps(deps-dev): update hypothesis requirement from >=6.165.2 to >=6.165.3 | skipped |
| Smart-Spam-Detector | #1 | deps(deps-dev): update pre-commit requirement from >=4.6.1 to >=4.6.2 | skipped |
| Statlas | #7 | chore(deps): bump lucide-react from 0.460.0 to 1.31.0 in /web | failure |
| Statlas | #5 | chore(deps): update pip-audit requirement from >=2.7 to >=2.10.1 | skipped |
| Statlas | #4 | chore(deps): update pydantic requirement from >=2.5 to >=2.13.4 | skipped |
| Statlas | #3 | chore(deps): update anthropic requirement from >=0.40 to >=0.121.0 | skipped |
| Statlas | #2 | chore(deps): update stripe requirement from >=8.0 to >=15.5.0 | skipped |
| Statlas | #1 | chore(deps): update ruff requirement from >=0.6 to >=0.16.2 | skipped |
| Tamasha | #19 | chore(deps)(deps): bump https://github.com/psf/black from 23.11.0 to 26.5.1 | failure |
| Tamasha | #10 | deps(deps): update pandas requirement from <3.0,>=2.0 to >=2.3.3,<3.0 | failure |
| Tamasha | #3 | chore(deps)(deps): bump actions/cache from 3 to 6 | failure |
| Tamasha | #2 | chore(deps)(deps): bump docker/build-push-action from 5 to 7 | failure |
| Tamasha | #1 | chore(deps)(deps): bump actions/checkout from 4 to 7 | failure |
| UNION-BANK- | #10 | chore(deps): bump pydantic-settings from 2.12.0 to 2.15.0 | skipped |
| UNION-BANK- | #9 | chore(deps): bump prometheus-client from 0.24.1 to 0.26.0 | skipped |
| UNION-BANK- | #8 | chore(deps): bump prettytable from 3.17.0 to 3.18.0 | skipped |
| UNION-BANK- | #7 | chore(deps): bump psutil from 7.1.0 to 7.2.2 | skipped |
| UNION-BANK- | #6 | chore(deps): bump osqp from 1.1.1 to 1.1.3 | skipped |
| UNION-BANK- | #5 | chore(deps): bump grpcio from 1.78.0 to 1.83.0 | skipped |
| UNION-BANK- | #4 | chore(deps): bump redis from 7.2.0 to 8.1.0 | skipped |
| UNION-BANK- | #3 | chore(deps): bump wrapt from 2.1.1 to 2.3.0 | skipped |
| UNION-BANK- | #2 | chore(deps): bump python-json-logger from 4.0.0 to 4.1.0 | skipped |
| UNION-BANK- | #1 | chore(deps): bump python-multipart from 0.0.9 to 0.0.32 | skipped |
| Veridoc | #29 | chore(deps): bump httpx from 0.27.2 to 0.28.1 in /backend | failure |
| Veridoc | #12 | chore(deps): bump actions/setup-python from 5 to 7 | failure |
| Veridoc | #9 | chore(deps): bump pytest from 8.3.3 to 9.1.1 in /backend | failure |
| Veridoc | #7 | chore(deps): bump pytest-asyncio from 0.24.0 to 1.4.0 in /backend | failure |
| Veridoc | #1 | Bump dependabot/fetch-metadata from 2 to 3 | failure |

### Needs human review (9)

| Repo | PR | Title |
|---|---|---|
| Veridoc | #8 | chore(deps-dev): bump typescript from 5.9.3 to 7.0.2 in /frontend |
| Veridoc | #10 | chore(deps): bump react-dom and @types/react-dom in /frontend |
| Veridoc | #16 | chore(deps-dev): bump @next/bundle-analyzer from 14.2.35 to 16.3.0 in /frontend |
| Veridoc | #17 | chore(deps): bump next from 14.2.35 to 16.3.0 in /frontend |
| Veridoc | #18 | chore(deps): bump react-dropzone from 14.4.1 to 20.1.0 in /frontend |
| Veridoc | #19 | chore(deps): bump react and @types/react in /frontend |
| Veridoc | #20 | chore(deps-dev): bump tailwindcss from 3.4.19 to 4.3.3 in /frontend |
| Veridoc | #21 | chore(deps-dev): bump eslint from 8.57.1 to 10.8.1 in /frontend |
| Veridoc | #25 | chore(deps): bump bcrypt from 4.0.1 to 5.0.0 in /backend |

## Blockers found

1. **Broken base-branch CI in 6 repos** (AegisAI, Book-Tale, Credit-Card-Fraud-Detection, Next-Gen-Reco, Price-My-Car, Tamasha) makes every Dependabot PR's CI signal untrustworthy. Example (AegisAI): `test` fails on `ImportError: cannot import name 'app' from 'worker'`; `security-scan` fails on Bandit B101 `assert_used` in test files. Fixing the baseline is a precondition for the merge sweep in those repos.
2. **`gh` auth**: the `GITHUB_TOKEN` env var in the shell is invalid/expired; the keyring token (themanoj-025) works. All commands must run with `GITHUB_TOKEN` unset.
3. **Veridoc holds**: 9 PRs carry `needs-human-review` (Next 16, React 19, eslint 10, tailwind 4, typescript 7 majors) - held by design pending CI-green re-evaluation.
4. **No merge executed in this pass** - per policy, each merge candidate requires local verification (Phase 2.3) before merging; this pass produced the inventory and classification only.