#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=notion
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

if [ -z "$NOTION_API_KEY" ]; then
  echo "Skipping Notion ingest test because the NOTION_API_KEY env var is not set."
  exit 8
fi

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  notion \
  --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --download-dir "$DOWNLOAD_DIR" \
  --notion-api-key "$NOTION_API_KEY" \
  --output-dir "$OUTPUT_DIR" \
  --database-ids "122b2c22996b435b9de2ee0e9d2b04bc" \
  --num-processes "$max_processes" \
  --recursive \
  --verbose \
  --work-dir "$WORK_DIR" \
  --max-retry-time 30

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
