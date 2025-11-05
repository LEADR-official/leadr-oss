#!/usr/bin/env bash

ENV=TEST uv run coverage run -m pytest $@

uv run coverage html
uv run coverage report --skip-covered --sort=Cover
