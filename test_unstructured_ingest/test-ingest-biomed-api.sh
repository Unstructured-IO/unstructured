#!/usr/bin/env bash
# shellcheck disable=SC2317

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=biomed-api
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

"$SCRIPT_DIR"/check-num-files-expected-output.sh 2 $OUTPUT_FOLDER_NAME 10k

PYTHONPATH=. ./unstructured/ingest/main.py \
    biomed \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes "$max_processes" \
    --strategy hi_res \
    --preserve-downloads \
    --re-download \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --api-from "2019-01-02" \
    --api-until "2019-01-02+00:03:10" \
    --decay .3 \
    --max-request-time 30 \
    --max-retries 5 \

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
