#!/usr/bin/env bash
set -e

# Description: This test checks if all the processed content is the same as the expected outputs.
# Also checks if a large table can be ingested properly.

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=airtable-diff
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

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

VARIED_DATA_BASE_ID="app5YQxSfp220fWtm"
VARIED_DATA_BASE_ID_2="appJ43QmP8I17zu88"

if [ -z "$AIRTABLE_PERSONAL_ACCESS_TOKEN" ]; then
  echo "Skipping Airtable ingest test because the AIRTABLE_PERSONAL_ACCESS_TOKEN is not set."
  exit 8
fi

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  airtable \
  --download-dir "$DOWNLOAD_DIR" \
  --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
  --list-of-paths "$VARIED_DATA_BASE_ID $VARIED_DATA_BASE_ID_2" \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.date,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth,metadatda.languages \
  --num-processes "$max_processes" \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --work-dir "$WORK_DIR" \
  --max-retry-time 10 \
  --verbose

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
