#!/usr/bin/env bash
# Statlas e2e server boot — seeds the fixture-demo dev DB, starts the FastAPI
# layer and the Next.js dev server, waits until both are ready, then keeps the
# pair running until this script is killed (Playwright's webServer lifecycle).
#
# Usage:  bash scripts/e2e-server.sh
# Env:    STATLAS_API_URL (default http://127.0.0.1:8000), PORT (default 3000)
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
API_PORT="${STATLAS_API_PORT:-8000}"
WEB_PORT="${PORT:-3000}"
API_URL="${STATLAS_API_URL:-http://127.0.0.1:${API_PORT}}"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///${ROOT}/data/dev.db}"
mkdir -p "${ROOT}/data"
export STATLAS_ENV="${STATLAS_ENV:-test}"
export CSRF_SECRET_KEY="${CSRF_SECRET_KEY:-e2e-csrf-secret-key-for-testing-only-32bytes}"

# Subcommand routing: "api-only" bootstraps the API + health endpoint
# (used by Playwright's webServer.slice api), "web-only" builds the web
# tier on top and serves the Next.js standalone server on :3000 (used by
# Playwright's webServer.slice web). Without a subcommand, boot the
# combined API + web stack.
case "${1:-}" in
  api-only)
    # Seeds the dev DB once (the web tier also seeds on its own boot), then
    # start the API layer only. The Next.js dev server is NOT started.
    echo "[e2e-server] api-only: seeding dev database..."
    cd "${ROOT}" && DATABASE_URL="${DATABASE_URL}" python "${ROOT}/scripts/seed_dev_db.py" || {
      echo "[e2e-server] api-only: seed failed" >&2
      exit 1
    }
    echo "[e2e-server] api-only: starting API on :${API_PORT}..."
    cd "${ROOT}" && DATABASE_URL="${DATABASE_URL}" STATLAS_ENV="${STATLAS_ENV:-test}" REPORTS_DEV_NARRATOR=1 python -m uvicorn app.api.main:app --host 127.0.0.1 --port "${API_PORT}" &
    API_PID=$!
    cleanup() { kill "$API_PID" 2>/dev/null; }
    trap cleanup EXIT INT TERM
    # Wait for readiness.
    for _ in $(seq 1 90); do
      if curl -sf -o /dev/null "http://127.0.0.1:${API_PORT}/api/v1/health"; then
        echo "[e2e-server] api-only: API ready."
        break
      fi
      sleep 1
    done
    wait
    ;;
  web-only)
    # Wait for the API slice to be healthy before building, so SSG prerendering finds real data.
    echo "[e2e-server] web-only: waiting for API on ${API_URL}/api/v1/health..."
    for _ in $(seq 1 90); do
      if curl -sf -o /dev/null "${API_URL}/api/v1/health"; then
        echo "[e2e-server] web-only: API ready."
        break
      fi
      sleep 1
    done
    echo "[e2e-server] web-only: building web (production build, matches CI)..."
    cd "${ROOT}/web" || exit 1
    STATLAS_API_URL="${API_URL}" NEXT_PUBLIC_STATLAS_API_URL="${API_URL}" npm run build || {
      echo "[e2e-server] web-only: web build failed" >&2
      exit 1
    }
    echo "[e2e-server] web-only: starting web (standalone) on :${WEB_PORT}..."
    STATLAS_API_URL="${API_URL}" NEXT_PUBLIC_STATLAS_API_URL="${API_URL}" npm run start -- --hostname 127.0.0.1 --port "${WEB_PORT}" &
    WEB_PID=$!
    cleanup() { kill "$WEB_PID" 2>/dev/null; }
    trap cleanup EXIT INT TERM
    wait
    ;;
  *)
    # Combined mode (original behavior).
    echo "[e2e-server] seeding dev database..."
    cd "${ROOT}" && DATABASE_URL="${DATABASE_URL}" python "${ROOT}/scripts/seed_dev_db.py" || {
      echo "[e2e-server] seed failed" >&2
      exit 1
    }
    echo "[e2e-server] starting API on :${API_PORT}..."
    cd "${ROOT}" && DATABASE_URL="${DATABASE_URL}" STATLAS_ENV="${STATLAS_ENV:-test}" REPORTS_DEV_NARRATOR=1 python -m uvicorn app.api.main:app --host 127.0.0.1 --port "${API_PORT}" &
    API_PID=$!

    echo "[e2e-server] building web (production build, matches CI)..."
    cd "${ROOT}/web" || exit 1
    STATLAS_API_URL="${API_URL}" NEXT_PUBLIC_STATLAS_API_URL="${API_URL}" npm run build || {
      echo "[e2e-server] web build failed" >&2
      exit 1
    }

    echo "[e2e-server] starting web (standalone) on :${WEB_PORT}..."
    STATLAS_API_URL="${API_URL}" NEXT_PUBLIC_STATLAS_API_URL="${API_URL}" npm run start -- --hostname 127.0.0.1 --port "${WEB_PORT}" &
    WEB_PID=$!

    cleanup() {
      echo "[e2e-server] shutting down (api=$API_PID web=$WEB_PID)"
      kill "$WEB_PID" "$API_PID" 2>/dev/null
    }
    trap cleanup EXIT INT TERM

    for _ in $(seq 1 90); do
      if curl -sf -o /dev/null "http://127.0.0.1:${API_PORT}/api/v1/health" &&
         curl -sf -o /dev/null "http://127.0.0.1:${WEB_PORT}/"; then
        echo "[e2e-server] API + web ready."
        break
      fi
      sleep 1
    done

    wait
    ;;
esac
