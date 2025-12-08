#!/usr/bin/env bash

PORT="${1:-8000}"

uv run uvicorn --app-dir src api.main:app --host 0.0.0.0 --port "$PORT" --reload
