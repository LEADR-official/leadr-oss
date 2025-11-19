#!/usr/bin/env bash

# fastapi run --host 0.0.0.0 src/api/main.py
uvicorn --app-dir src api.main:app --host 0.0.0.0 --port 8000
