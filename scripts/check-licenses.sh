#!/usr/bin/env bash

set -euo pipefail

# Generate a frozen requirements list from the uv-managed environment
# and check all dependencies for authorized licenses.
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

uv pip freeze > "$TMPFILE"

echo "Checking licenses for installed packages..."
liccheck -r "$TMPFILE"
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "All dependencies have authorized licenses."
else
  echo "There are dependencies with unauthorized or unknown licenses."
  exit 1
fi
