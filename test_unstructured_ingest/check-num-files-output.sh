#!/usr/bin/env bash

# Description: Validate that the number of files in the output directory is as expected.
#
# Arguments:
#   - $1: The expected number of files in the output directory.
#   - $2: Name of the output folder. This is used to determine the structured output path.

set +e

EXPECTED_NUM_FILES=$1
OUTPUT_FOLDER_NAME=$2
SCRIPT_DIR=$(dirname "$(realpath "$0")")
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
num_files_created="$(find "$OUTPUT_DIR" -type f -exec printf '.' \; | wc -c | xargs)"

# Note: single brackets and "-ne" operator were necessary for evaluation in CI
if [ "$num_files_created" -ne "$EXPECTED_NUM_FILES" ] && [ "$OVERWRITE_FIXTURES" != "true" ]; then
  echo
  echo "ERROR: $num_files_created files created. $EXPECTED_NUM_FILES files should have been created."
  exit 1
fi
