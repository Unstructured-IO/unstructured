#!/usr/bin/env bash

# Description: Validate that the number of directories in the output directory is as expected.
#
# Arguments:
#   - $1: The expected number of directories in the output directory.
#   - $2: Name of the output folder. This is used to determine the structured output path.

set +e

EXPECTED_NUM_DIRS=$1
OUTPUT_FOLDER_NAME=$2
SCRIPT_DIR=$(dirname "$(realpath "$0")")
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME

NUMBER_OF_FOUND_DIRS="$(find "$OUTPUT_DIR" -type d -exec printf '.' \; | wc -c | xargs)"

# Note: single brackets and "-ne" operator were necessary for evaluation in CI
if [ "$NUMBER_OF_FOUND_DIRS" -ne "$EXPECTED_NUM_DIRS" ]; then
  echo
  echo "$EXPECTED_NUM_DIRS directories were expected to be found."
  echo "$NUMBER_OF_FOUND_DIRS directories were found instead."
  echo "Name of the directories found:"
  find "$OUTPUT_DIR" -type d
  exit 1
fi
