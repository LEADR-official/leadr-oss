#!/usr/bin/env bash

rm -rf site-md

uv run griffe2md src/leadr -o site-md/reference.md

# Generate OpenAPI spec + HTTP docs...

