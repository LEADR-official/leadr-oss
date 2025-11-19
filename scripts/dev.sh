#!/usr/bin/env bash

# uv run fastapi run --host 0.0.0.0 src/api/main.py
uv run uvicorn --app-dir src api.main:app --host 0.0.0.0 --port 8000 --reload
