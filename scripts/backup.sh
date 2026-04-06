#!/usr/bin/env bash
set -e

uv run python -m leadr.common.utils.backup "$@"
