#!/usr/bin/env bash

# Description: Compare the structured output files to the expected output files and exit with an error
#              if they are different. If the environment variable OVERWRITE_FIXTURES is not "false",
#              then this script will instead copy the output files to the expected output directory.
#
# Arguments:
#   - $1: Name of the output folder. This is used to determine the output directory and the expected output directory paths.
#
# Environment Variables:
#   - OVERWRITE_FIXTURES: Controls whether to overwrite fixtures or not. default: "false"

set +e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}
TMP_DIRECTORY_CLEANUP=${TMP_DIRECTORY_CLEANUP:-true}
OUTPUT_FOLDER_NAME=$1
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
OUTPUT_DIR_TEXT=$OUTPUT_ROOT/text-output/$OUTPUT_FOLDER_NAME
EXPECTED_OUTPUT_DIR=$OUTPUT_ROOT/expected-structured-output/$OUTPUT_FOLDER_NAME
EXPECTED_OUTPUT_DIR_TEXT=$OUTPUT_ROOT/expected-text-output/$OUTPUT_FOLDER_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  if [ "$TMP_DIRECTORY_CLEANUP" == "true" ]; then
    cleanup_dir "$EXPECTED_OUTPUT_DIR_TEXT"
    cleanup_dir "$OUTPUT_DIR_TEXT"
  else
    echo "skipping tmp directory cleanup"
  fi
}

trap cleanup EXIT

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [ "$OVERWRITE_FIXTURES" != "false" ]; then
  # remove folder if it exists
  if [ -d "$EXPECTED_OUTPUT_DIR" ]; then
    rm -rf "$EXPECTED_OUTPUT_DIR"
  fi
  mkdir -p "$EXPECTED_OUTPUT_DIR"
  cp -rf "$OUTPUT_DIR" "$OUTPUT_ROOT/expected-structured-output"
elif ! diff -ru "$EXPECTED_OUTPUT_DIR" "$OUTPUT_DIR"; then
  "$SCRIPT_DIR"/json-to-clean-text-folder.sh "$EXPECTED_OUTPUT_DIR" "$EXPECTED_OUTPUT_DIR_TEXT"
  "$SCRIPT_DIR"/json-to-clean-text-folder.sh "$OUTPUT_DIR" "$OUTPUT_DIR_TEXT"
  "$SCRIPT_DIR"/clean-permissions-files.sh "$OUTPUT_DIR_TEXT"
  diff -ru "$EXPECTED_OUTPUT_DIR_TEXT" "$OUTPUT_DIR_TEXT" >outputdiff.txt
  cat outputdiff.txt
  diffstat -c outputdiff.txt
  echo
  echo "There are differences from the previously checked-in structured outputs."
  echo
  echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
  echo
  echo "  export OVERWRITE_FIXTURES=true"
  echo
  echo "and then rerun this script."
  echo
  echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
  echo "to update fixtures for CI."
  echo
  exit 1
fi
