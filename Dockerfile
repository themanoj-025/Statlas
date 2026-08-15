# Statlas API — production image (FastAPI + uvicorn)
#
# Multi-stage not needed (pure-Python runtime): a single slim stage keeps it
# simple. Dependencies install first (layer caching), then the code, then we
# drop to a non-root user (Constitution §4 security posture).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Non-root runtime user. data/ is writable by it because the `seed` compose
# service runs scripts/seed_dev_db.py (writes data/coverage_matrix.json).
RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data && chown -R app:app /app

USER app

EXPOSE 8000

# Health endpoint: /api/v1/health (the compose healthcheck curls this).
# The whole Python runtime lives in the app/ package (Ultra Restructure).
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
