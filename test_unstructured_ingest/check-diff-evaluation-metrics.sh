#!/usr/bin/env bash

# Description: Compare the current evaluation metrics to the previoud evaluation metrics and exit 
#              with an error if they are different. If the environment variable OVERWRITE_FIXTURES 
#              is not "false", then this script will instead copy the output files to the expected
#              output directory.
#
# Environment Variables:
#   - OVERWRITE_FIXTURES: Controls whether to overwrite fixtures or not. default: "false"

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}
TMP_DIRECTORY_CLEANUP=${TMP_DIRECTORY_CLEANUP:-true}
OUTPUT_FOLDER_NAME=$1
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
TMP_METRICS_LATEST_RUN_DIR=$OUTPUT_ROOT/metrics-tmp/$OUTPUT_FOLDER_NAME
METRICS_DIR=$OUTPUT_ROOT/metrics/$OUTPUT_FOLDER_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  if [ "$TMP_DIRECTORY_CLEANUP" == "true" ]; then
    cleanup_dir "$TMP_METRICS_LATEST_RUN_DIR"
  else
    echo "skipping tmp directory cleanup"
  fi
}

trap cleanup EXIT

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [ "$OVERWRITE_FIXTURES" != "false" ]; then
    # remove folder if it exists
    if [ -d "$METRICS_DIR" ]; then
        find "$METRICS_DIR" -maxdepth 1 -type f ! -name "metrics-json-manifest.txt" -exec rm -rf {} +
    fi
    # force copy (overwrite) files from metrics-tmp (new eval metrics) to metrics (old eval metrics)
    mkdir -p "$METRICS_DIR"
    cp -rf "$TMP_METRICS_LATEST_RUN_DIR" "$OUTPUT_ROOT/metrics"
elif ! diff -ru "$METRICS_DIR" "$TMP_METRICS_LATEST_RUN_DIR" ; then
    "$SCRIPT_DIR"/clean-permissions-files.sh "$TMP_METRICS_LATEST_RUN_DIR"
    diff -r "$METRICS_DIR" "$TMP_METRICS_LATEST_RUN_DIR"> metricsdiff.txt
    cat metricsdiff.txt
    diffstat -c metricsdiff.txt
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
