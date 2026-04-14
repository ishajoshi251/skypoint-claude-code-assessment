#!/bin/sh
# =============================================================================
# TalentBridge API entrypoint
# Runs: migrations → seed (idempotent) → uvicorn
# =============================================================================
set -e

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Running seed script (idempotent)..."
python -m app.db.seed

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
