#!/usr/bin/env bash
set -e

# Description: This test checks if the number of spaces and documents processed are as expected.
# Each space shows up as a directory in the output folder, hence check-num-dirs-output.sh
# Each document shows up as a file in a space directory, hence check-num-files-output.sh

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=confluence-large
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

if [ -z "$CONFLUENCE_USER_EMAIL" ] || [ -z "$CONFLUENCE_API_TOKEN" ]; then
  echo "Skipping Confluence ingest test because the CONFLUENCE_USER_EMAIL or CONFLUENCE_API_TOKEN env var is not set."
  exit 8
fi

# The test checks the scenario where --confluence-list-of-spaces and --confluence-num-of-spaces
# are being provided at the same time, which is a wrong way to use the connector.

# We expect the test to ignore --confluence-num-of-spaces and use --confluence-list-of-spaces.
RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  confluence \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --url https://unstructured-ingest-test.atlassian.net \
  --user-email "$CONFLUENCE_USER_EMAIL" \
  --api-token "$CONFLUENCE_API_TOKEN" \
  --max-num-of-spaces 10 \
  --spaces testteamsp1 \
  --max-num-of-docs-from-each-space 250 \
  --work-dir "$WORK_DIR"

OUTPUT_SUBFOLDER_NAME=testteamsp1

# We are expecting two directories: one for the space, and one is the output directory itself
# Example:
# Output dir: unstructured/test_unstructured_ingest/structured-output/confluence-large
# Space dir: unstructured/test_unstructured_ingest/structured-output/confluence-large/testteamsp1
"$SCRIPT_DIR"/check-num-dirs-output.sh 2 "$OUTPUT_FOLDER_NAME"

# We are expecting 250 files due to the --confluence-num-of-docs-from-each-space 250 that we provided.
"$SCRIPT_DIR"/check-num-files-output.sh 250 "$OUTPUT_FOLDER_NAME"/"$OUTPUT_SUBFOLDER_NAME"/
