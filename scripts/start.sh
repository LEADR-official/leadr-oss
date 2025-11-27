#!/usr/bin/env bash
set -e

# Optionally run database migrations before starting the app
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# Enable live reload in development
if [ "$ENV" = "DEV" ]; then
    uvicorn --app-dir src api.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
else
    uvicorn --app-dir src api.main:app --host 0.0.0.0 --port ${PORT:-8000}
fi
