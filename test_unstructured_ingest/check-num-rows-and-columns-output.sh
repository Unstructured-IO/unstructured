#!/usr/bin/env bash

# Description: Validate that the number of rows in the output dataframe is as expected.
#
# Arguments:
#   - $1: The expected number of rows in the dataframe.
#   - $2: The path for the structured output file.

SCRIPT_PATH="scripts/airtable-test-helpers/print_num_rows_df.py"

EXPECTED_ROWS=$1
OUTPUT_FILE_NAME=$2

# Run the Python script and capture its output
ROWS=$(python "$SCRIPT_PATH" --structured-output-file-path "$OUTPUT_FILE_NAME")

# Compare the actual output with the expected output
if [[ $ROWS -ne $EXPECTED_ROWS ]]; then
  echo
  echo "ERROR:  $ROWS rows created. $EXPECTED_ROWS rows should have been created."
  exit 1
fi
