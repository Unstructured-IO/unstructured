#!/usr/bin/env bash

# Description: Compare the structured output markdown files to the expected output markdown files and exit
#              with an error if they are different. If the environment variable OVERWRITE_FIXTURES
#              is not "false", then this script will instead copy the output files to the expected
#              output directory.
#
# Environment Variables:
#   - OVERWRITE_FIXTURES: Controls whether to overwrite markdown fixtures or not. default: "false"

set +e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}
TMP_DIRECTORY_CLEANUP=${TMP_DIRECTORY_CLEANUP:-true}
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR_MARKDOWN=$OUTPUT_ROOT/structured-markdown-output
EXPECTED_OUTPUT_DIR_MARKDOWN=$OUTPUT_ROOT/expected-structured-output-markdown
DIFF_OUTPUT_FILE="outputmarkdowndiff.txt"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  if [ "$TMP_DIRECTORY_CLEANUP" == "true" ]; then
    cleanup_dir "$OUTPUT_DIR_MARKDOWN"
  else
    echo "skipping tmp directory cleanup"
  fi
}

trap cleanup EXIT

# Generate structured HTML output
"$SCRIPT_DIR"/structured-json-to-markdown.sh "$OUTPUT_DIR_MARKDOWN"

# To update ingest test HTML fixtures, run 'make html-fixtures-update' on x86_64
if [ "$OVERWRITE_FIXTURES" != "false" ]; then
  # remove folder if it exists
  if [ -d "$EXPECTED_OUTPUT_DIR_MARKDOWN" ]; then
    rm -rf "$EXPECTED_OUTPUT_DIR_MARKDOWN"
  fi
  mkdir -p "$EXPECTED_OUTPUT_DIR_MARKDOWN"
  cp -rf "$OUTPUT_DIR_MARKDOWN"/* "$EXPECTED_OUTPUT_DIR_MARKDOWN"
elif ! diff -ru "$EXPECTED_OUTPUT_DIR_MARKDOWN" "$OUTPUT_DIR_MARKDOWN"; then
  diff -ru "$EXPECTED_OUTPUT_DIR_MARKDOWN" "$OUTPUT_DIR_MARKDOWN" >"$DIFF_OUTPUT_FILE"
  cat "$DIFF_OUTPUT_FILE"
  diffstat -c "$DIFF_OUTPUT_FILE"
  echo
  echo "There are differences from the previously checked-in structured markdown outputs."
  echo
  echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
  echo
  echo "  export OVERWRITE_FIXTURES=true"
  echo
  echo "and then rerun this script."
  echo
  echo "NOTE: You'll likely just want to run 'make markdown-fixtures-update' on x86_64 hardware"
  echo "to update fixtures for CI."
  echo
  exit 1
fi
