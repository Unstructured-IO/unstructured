#!/usr/bin/env bash
set -e

# Description: This test checks if the number of bases and tables processed are as expected.
# Each base shows up as a directory in the output folder, hence check-num-dirs-output.sh
# Each table shows up as a file in a base directory, hence check-num-files-output.sh

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=airtable-large
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

if [ -z "$AIRTABLE_PERSONAL_ACCESS_TOKEN" ]; then
  echo "Skipping Airtable ingest test because the AIRTABLE_PERSONAL_ACCESS_TOKEN is not set."
  exit 8
fi

# Provides component IDs such as LARGE_TEST_LIST_OF_PATHS,
# LARGE_TABLE_BASE_ID, LARGE_TABLE_TABLE_ID, and LARGE_BASE_BASE_ID
# shellcheck disable=SC1091
source ./scripts/airtable-test-helpers/component_ids.sh

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  airtable \
  --download-dir "$DOWNLOAD_DIR" \
  --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
  --list-of-paths "$LARGE_TEST_LIST_OF_PATHS" \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.date,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --work-dir "$WORK_DIR"

# We are expecting fifteen directories: fourteen bases and the parent directory
"$SCRIPT_DIR"/check-num-dirs-output.sh 15 "$OUTPUT_FOLDER_NAME"

# We are expecting 101 files: 100 tables and the parent directory
"$SCRIPT_DIR"/check-num-files-output.sh 101 "$OUTPUT_FOLDER_NAME"/"$LARGE_BASE_BASE_ID"/

# Test on ingesting a large number of bases
for i in {1..12}; do
  var="LARGE_WORKSPACE_BASE_ID_$i"
  "$SCRIPT_DIR"/check-num-files-output.sh 12 "$OUTPUT_FOLDER_NAME"/"${!var}"
done

# Test on ingesting a table with lots of rows
"$SCRIPT_DIR"/check-num-rows-and-columns-output.sh 39999 "$OUTPUT_DIR"/"$LARGE_TABLE_BASE_ID"/"$LARGE_TABLE_TABLE_ID".json
