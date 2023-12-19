#!/usr/bin/env bash

# Description: Validate that the number of files in the output directory is as expected.
#
# Arguments:
#   - $1: The expected number of files in the output directory.
#   - $2: Name of the output folder. This is used to determine the output directory and the expected output directory paths.
#   - $3: The expected size of the output directory in bytes (e.g. "10k").

set +e

EXPECTED_NUM_FILES=$1
OUTPUT_FOLDER_NAME=$2
EXPECTED_SIZE=$3
SCRIPT_DIR=$(dirname "$(realpath "$0")")
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
EXPECTED_OUTPUT_DIR=$OUTPUT_ROOT/expected-structured-output/$OUTPUT_FOLDER_NAME
NUM_FILES=$(find "$EXPECTED_OUTPUT_DIR" -type f -size +"$EXPECTED_SIZE" | wc -l)

# Note: single brackets and "-ne" operator were necessary for evaluation in CI
if [ "$NUM_FILES" -ne "$EXPECTED_NUM_FILES" ] && [ "$OVERWRITE_FIXTURES" != "true" ]; then
  echo "The test fixtures in $EXPECTED_OUTPUT_DIR look suspicious."
  echo "Expected $EXPECTED_NUM_FILES files, but found $NUM_FILES files found."
  echo "Did you overwrite test fixtures with bad outputs?"
  exit 1
fi
