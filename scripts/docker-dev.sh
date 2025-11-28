#!/bin/bash
# Development docker compose wrapper
# Ensures .env file is correctly loaded for variable substitution
set -e
cd "$(dirname "$0")/.." || exit 1
docker compose -f docker/docker-compose.dev.yml --env-file .env "$@"
