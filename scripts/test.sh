#!/usr/bin/env bash

PYTHONDONTWRITEBYTECODE=1 ENV=TEST uv run coverage run -m pytest -p no:pastebin -p no:nose -p no:doctest $@

uv run coverage html
uv run coverage report --skip-covered --sort=Cover
