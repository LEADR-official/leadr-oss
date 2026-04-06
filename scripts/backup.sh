#!/usr/bin/env bash
set -e

uv run python scripts/backup_db.py "$@"
