#!/usr/bin/env bash

# Description: Compare the current evaluation metrics to the previoud evaluation metrics and exit 
#              with an error if they are different. If the environment variable OVERWRITE_FIXTURES 
#              is not "false", then this script will instead copy the output files to the expected
#              output directory.
#
# Environment Variables:
#   - OVERWRITE_FIXTURES: Controls whether to overwrite fixtures or not. default: "false"

set +e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}
TMP_DIRECTORY_CLEANUP=${TMP_DIRECTORY_CLEANUP:-true}
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/metrics-tmp
EXPECTED_OUTPUT_DIR=$OUTPUT_ROOT/metrics

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
    cleanup_dir "$OUTPUT_DIR"
}

trap cleanup EXIT

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [ "$OVERWRITE_FIXTURES" != "false" ]; then
    # force copy (overwrite) files from metrics-tmp (new eval metrics) to metrics (old eval metrics)
    cp -rf "$OUTPUT_DIR" "$EXPECTED_OUTPUT_DIR"
elif ! diff -ru "$EXPECTED_OUTPUT_DIR" "$OUTPUT_DIR" ; then
    "$SCRIPT_DIR"/clean-permissions-files.sh "$OUTPUT_DIR"
    diff -r "$EXPECTED_OUTPUT_DIR" "$OUTPUT_DIR"> outputdiff.txt
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
