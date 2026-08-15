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

# Windows/Git-Bash path-proofing: bash sees /f/GITHUB/Statlas but native Python
# needs F:/GITHUB/Statlas. `cygpath -m` converts when available; on Linux CI it
# passes the path through unchanged.
if command -v cygpath >/dev/null 2>&1; then
  ROOT_WIN="$(cygpath -m "${ROOT}")"
else
  ROOT_WIN="${ROOT}"
fi
DB_URL="sqlite+pysqlite:///${ROOT_WIN}/data/dev.db"

# The dev DB is built through the REAL pipeline from labeled fixtures + the
# deterministic synthetic leagues (scripts/seed_dev_db.py) — the same dataset
# the API smoke tests use. Rebuilt on every e2e boot so tests are hermetic.
echo "[e2e-server] seeding dev database..."
cd "${ROOT}" && python "${ROOT}/scripts/seed_dev_db.py" >/dev/null 2>&1 || {
  echo "[e2e-server] seed failed" >&2
  exit 1
}

echo "[e2e-server] starting API on :${API_PORT}..."
cd "${ROOT}" && DATABASE_URL="${DB_URL}" python -m uvicorn app.api.main:app --host 127.0.0.1 --port "${API_PORT}" &
API_PID=$!

echo "[e2e-server] building web (production build, matches CI)..."
cd "${ROOT}/web" || exit 1
STATLAS_API_URL="${API_URL}" npm run build >/dev/null 2>&1 || {
  echo "[e2e-server] web build failed" >&2
  exit 1
}

echo "[e2e-server] starting web (standalone) on :${WEB_PORT}..."
STATLAS_API_URL="${API_URL}" npm run start -- --hostname 127.0.0.1 --port "${WEB_PORT}" &
WEB_PID=$!

cleanup() {
  echo "[e2e-server] shutting down (api=$API_PID web=$WEB_PID)"
  kill "$WEB_PID" "$API_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Wait for readiness (poll health endpoints).
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null "http://127.0.0.1:${API_PORT}/api/v1/health" &&
     curl -sf -o /dev/null "http://127.0.0.1:${WEB_PORT}/"; then
    echo "[e2e-server] API + web ready."
    break
  fi
  sleep 1
done

wait
