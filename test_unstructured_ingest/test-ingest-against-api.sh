#!/usr/bin/env bash

set -e

if [ -z "$UNS_API_KEY" ]; then
   echo "Skipping ingest test against api because the UNS_API_KEY env var is not set."
   exit 0
fi
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=api-ingest-output
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --api-key "$UNS_API_KEY" \
    --metadata-exclude coordinates,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --partition-by-api \
    --strategy hi_res \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --num-processes "$max_processes" \
    --file-glob "*1p.txt" \
    --input-path example-docs \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-num-files-output.sh 1 $OUTPUT_FOLDER_NAME
