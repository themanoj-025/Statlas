# ═══════════════════════════════════════════════════════════════════════
# Statlas — Build, Test, Lint, and Deploy commands
# ═══════════════════════════════════════════════════════════════════════

.PHONY: help setup test lint format typecheck run-api run-streamlit \
        db-init db-migrate db-seed docker-up docker-down docker-logs \
        clean install-dev

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────

setup: ## Install dependencies and set up the project
	pip install -r requirements.txt
	pre-commit install

install-dev: ## Install dev dependencies (test + lint + typecheck)
	pip install -r requirements.txt
	pip install pytest pytest-cov ruff mypy black isort pre-commit
	pre-commit install

# ── Test ─────────────────────────────────────────────────────────────

test: ## Run pytest with coverage
	pytest tests/ -v --tb=short --cov=app --cov-report=term-missing -W ignore::DeprecationWarning

test-fast: ## Run tests without coverage (faster)
	pytest tests/ -v --tb=short -x -W ignore::DeprecationWarning

test-ml: ## Run clustering and ML tests only
	pytest tests/test_clustering.py -v --tb=short

# ── Lint & Format ───────────────────────────────────────────────────

lint: ## Run linters (ruff + mypy)
	ruff check app/ tests/ scripts/
	mypy app/ --ignore-missing-imports

format: ## Auto-format code (ruff + black)
	ruff check --fix app/ tests/ scripts/
	black app/ tests/ scripts/
	isort app/ tests/ scripts/

typecheck: ## Run mypy type checking
	mypy app/ --ignore-missing-imports

# ── Run ──────────────────────────────────────────────────────────────

run-api: ## Run the FastAPI server
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-streamlit: ## Run the Streamlit dashboard
	streamlit run app/ui/main.py

run-dev: ## Run both API and Streamlit (background)
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
	streamlit run app/ui/main.py --server.port 8501

# ── Database ─────────────────────────────────────────────────────────

db-init: ## Initialize the database
	python -c "from app.database import init_db; init_db()"

db-seed: ## Seed the database with demo data
	python scripts/seed_dev_db.py

db-migrate: ## Run database migrations (if using Alembic)
	alembic upgrade head

# ── Docker ───────────────────────────────────────────────────────────

docker-up: ## Start the full dev stack
	docker compose up --build -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f --tail=100

docker-build: ## Build Docker images
	docker compose build

docker-test: ## Run tests inside the Docker container
	docker compose exec web pytest tests/ -v

# ── ML Pipeline ──────────────────────────────────────────────────────

ingest: ## Ingest real data from Transfermarkt
	python scripts/ingest_real_data.py

cluster: ## Train clustering model
	python -c "from app.compute.clustering import train_clustering_model; print('Use the API endpoint to train')"

# ── Clean ────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache htmlcov/ .coverage
