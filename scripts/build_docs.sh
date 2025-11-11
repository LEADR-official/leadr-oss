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

echo "Generating Python API reference..."
uv run griffe2md src/leadr -o site-md/reference.md

echo "Creating documentation index..."
cat > site-md/index.md <<'EOF'
# LEADR API Documentation

Welcome to the LEADR API documentation.

## Documentation Sections

### [Python API Reference](reference.md)
Complete reference for all Python modules, classes, and functions in the LEADR codebase.

<!-- TODO: Add OpenAPI/REST API documentation section once implemented -->

## Quick Links

- [GitHub Repository](https://github.com/LEADR-official/leadr-oss)
- [Getting Started Guide](https://github.com/LEADR-official/leadr-oss#readme)

<!-- TODO: Add more navigation links as documentation grows -->

EOF

# TODO: Generate OpenAPI specification
# Uncomment and implement when ready:
#
# echo "Generating OpenAPI specification..."
# # Option 1: Extract from running FastAPI app
# # python -c "from src.api.main import app; import json; print(json.dumps(app.openapi()))" > site-md/openapi.json
#
# # Option 2: Start server temporarily and fetch
# # uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
# # SERVER_PID=$!
# # sleep 2  # Wait for server to start
# # curl http://localhost:8000/openapi.json > site-md/openapi.json
# # kill $SERVER_PID

# TODO: Generate REST API documentation from OpenAPI spec
# Uncomment and implement when ready:
#
# echo "Generating REST API documentation..."
# # Convert OpenAPI spec to markdown using your preferred tool
# # Examples:
# # - widdershins: npx widdershins site-md/openapi.json -o site-md/api-reference.md
# # - openapi-markdown: npx openapi-markdown -i site-md/openapi.json -o site-md/api-reference.md
# # - custom Python script using pydantic-openapi-schema

echo "Documentation build complete!"
echo "Output directory: site-md/"
ls -lh site-md/
