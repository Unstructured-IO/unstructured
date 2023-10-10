#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --num-processes "$max_processes" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --strategy hi_res \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --file-glob "*.html" \
    --input-path example-docs \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-num-files-output.sh 12 $OUTPUT_FOLDER_NAME
