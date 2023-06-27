#!/usr/bin/env bash

# Description: Validate that the number of files in the output directory is as expected.
#
# Arguments:
#   - $1: The expected number of files in the output directory.
#   - $2: Name of the output folder. This is used to determine the test directory path.

set +e

EXPECTED_NUM_FILES=$1
OUTPUT_FOLDER_NAME=$2
EXPECTED_OUTPUT_DIR=$SCRIPT_DIR/expected-structured-output/$OUTPUT_FOLDER_NAME

if [ "$(find "$EXPECTED_OUTPUT_DIR" -type f -printf '.' | wc -c)" != "$EXPECTED_NUM_FILES" ]; then
   echo
   echo "$EXPECTED_NUM_FILES files should have been created."
   exit 1
fi