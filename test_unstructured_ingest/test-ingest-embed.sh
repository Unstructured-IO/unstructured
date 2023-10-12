#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=embed
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
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --reprocess \
    --input-path example-docs/fake-text-utf-16.txt \
    --work-dir "$WORK_DIR" \
    --embedding-api-key "$OPENAI_API_KEY"

set +e

# currently openai encoder is non-deterministic
# once we have an alternative encoder that is deterministic, we test the diff here
# until then just validating the file was created
"$SCRIPT_DIR"/check-num-files-output.sh 1 "$OUTPUT_FOLDER_NAME"
