#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=azure
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    azure \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes "$max_processes" \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --account-name azureunstructured1 \
    --remote-url abfs://container1/ \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
