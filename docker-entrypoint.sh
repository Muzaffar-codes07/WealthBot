#!/bin/bash
set -euo pipefail

echo "=== Running database migrations ==="
if ! alembic upgrade head; then
  echo "FATAL: Alembic migration failed. Not starting the API." >&2
  exit 1
fi

echo "=== Starting WealthBot API ==="
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${UVICORN_WORKERS:-2}"
