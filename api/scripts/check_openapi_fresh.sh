#!/usr/bin/env bash
# Check that openapi.json matches the live FastAPI spec.
# Exits 1 if the committed spec is stale.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_SPEC="$(mktemp /tmp/openapi_XXXXXX.json)"

cd "$REPO_ROOT"
python api/scripts/export_openapi.py --output "$TMP_SPEC" 2>/dev/null || \
  python api/scripts/export_openapi.py

if diff -q openapi.json "$TMP_SPEC" > /dev/null 2>&1; then
  echo "✓ openapi.json is up to date"
  rm -f "$TMP_SPEC"
  exit 0
else
  echo "✗ openapi.json is STALE — run 'make generate' to update"
  diff openapi.json "$TMP_SPEC" || true
  rm -f "$TMP_SPEC"
  exit 1
fi
