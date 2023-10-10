#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-single-file-with-encoding
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
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --output-dir "$OUTPUT_DIR" \
    --encoding cp1252 \
    --verbose \
    --reprocess \
    --input-path example-docs/fake-html-cp1252.html \
    --work-dir "$WORK_DIR"

set +e

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
