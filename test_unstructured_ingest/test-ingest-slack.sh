#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=slack
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
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

if [ -z "$SLACK_TOKEN" ]; then
   echo "Skipping Slack ingest test because the SLACK_TOKEN env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
   slack \
   --num-processes "$max_processes" \
   --download-dir "$DOWNLOAD_DIR" \
   --metadata-exclude coordinates,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
   --strategy hi_res \
   --preserve-downloads \
   --reprocess \
   --output-dir "$OUTPUT_DIR" \
   --verbose \
   --channels C052BGT7718 \
   --token "${SLACK_TOKEN}" \
   --start-date 2023-04-01 \
   --end-date 2023-04-08T12:00:00-08:00 \
   --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
