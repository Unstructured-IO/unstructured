#!/usr/bin/env bash

# Description: Validate that the number of files in the output directory is as expected.
#
# Arguments:
#   - $1: The expected number of files in the output directory.
#   - $2: Name of the output folder. This is used to determine the test directory path.
#  - $3: The expected size of the output directory in bytes (e.g. 10k).

set +e

EXPECTED_NUM_FILES=$1
OUTPUT_FOLDER_NAME=$2
EXPECTED_SIZE=$3
EXPECTED_OUTPUT_DIR=$SCRIPT_DIR/expected-structured-output/$OUTPUT_FOLDER_NAME


if [[ "$(find "$EXPECTED_OUTPUT_DIR" -type f -size +"$EXPECTED_SIZE" | wc -l)" -ne "$EXPECTED_NUM_FILES" ]]; then
    echo "The test fixtures in $EXPECTED_OUTPUT_DIR look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi