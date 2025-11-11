#!/usr/bin/env bash

set -e  # Exit on any error

echo "Building documentation..."

# Clean and create output directory
rm -rf site-md
mkdir -p site-md

# Determine version for .api-version file
if [ -n "$VERSION" ]; then
  # Use VERSION from environment (set by CI)
  API_VERSION="$VERSION"
else
  # Try to get latest git tag for local builds
  API_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "dev")
fi

echo "API Version: $API_VERSION"
echo "$API_VERSION" > site-md/.api-version

echo "Copying static documentation from docs/..."
if [ -d "docs" ]; then
  cp -r docs/* site-md/
  echo "Copied static documentation files"
else
  echo "Warning: docs/ directory not found"
  exit 1
fi

echo "Generating Python API reference..."
uv run griffe2md src/leadr -o site-md/reference.md

echo "Generating OpenAPI specification..."
uv run --directory src python -c "from api.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > site-md/openapi.json
if [ $? -ne 0 ]; then
  echo "Error: Failed to generate OpenAPI specification"
  exit 1
fi
echo "Generated site-md/openapi.json"

echo "Generating HTTP API documentation..."
widdershins site-md/openapi.json -o site-md/http-api.md --language_tabs 'curl:curl' 'python:Python' 'javascript:Javascript' --summary
if [ $? -ne 0 ]; then
  echo "Error: Failed to convert OpenAPI spec to markdown"
  echo "Make sure widdershins is installed: npm install -g widdershins"
  exit 1
fi
echo "Generated site-md/http-api.md"

echo "Transforming API docs to MkDocs format..."
uv run python scripts/transform_api_docs.py site-md/http-api.md site-md/http-api.md.tmp
if [ $? -ne 0 ]; then
  echo "Error: Failed to transform API documentation"
  exit 1
fi
mv site-md/http-api.md.tmp site-md/http-api.md
echo "Transformed site-md/http-api.md for MkDocs compatibility"

echo "Documentation build complete!"
echo "Output directory: site-md/"
ls -lh site-md/
