# Statlas API — production image (FastAPI + uvicorn)
#
# Multi-stage build: builder stage installs dependencies (including any
# build tools for C extensions), runtime stage is minimal slim image.
# This keeps the final image lean and reduces attack surface.

# ── Stage 1: builder ──────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder (no build tools in final image)
COPY --from=builder /install /usr/local

# Non-root runtime user. data/ is writable by it because the `seed` compose
# service runs scripts/seed_dev_db.py (writes data/coverage_matrix.json).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

COPY . .

RUN mkdir -p data && chown -R app:app /app

USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Health endpoint: /api/v1/health (the compose healthcheck curls this).
# --workers 4 for production (handles concurrent requests; adjust based on CPU).
# --timeout-keep-alive 65 for load-balancer health checks.
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "65"]
