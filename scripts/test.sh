#!/usr/bin/env bash

PYTHONDONTWRITEBYTECODE=1 ENV=TEST uv run pytest \
	--cov=src \
	--cov-report html \
	-n auto -p no:pastebin -p no:nose -p no:doctest \
	$@

uv run coverage report --sort=Cover --skip-covered
