#!/usr/bin/env bash

# shellcheck disable=SC2317  # Shellcheck complains that trap functions are unreachable...

LICCHECK_FILE="${PWD}/requirements-liccheck.txt"

pip freeze >"$LICCHECK_FILE"

liccheck -r "$LICCHECK_FILE"
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
  echo "All dependencies have authorized licenses."
  rm "$LICCHECK_FILE"
  exit 0
else
  echo "There are dependencies with unauthorized or unknown licenses."
  rm "$LICCHECK_FILE"
  exit 1
fi
