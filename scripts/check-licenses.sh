#!/usr/bin/env bash

REQUIREMENTS_FILES=$(find requirements -type f -name "*.txt" ! -name "constraints.txt")

for REQUIREMENTS_FILE in $REQUIREMENTS_FILES; do
  echo "Checking $REQUIREMENTS_FILE"
  liccheck -r "$REQUIREMENTS_FILE"
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo "All dependencies have authorized licenses."
  else
    echo "There are dependencies with unauthorized or unknown licenses."
    exit 1
  fi
done

exit 0
