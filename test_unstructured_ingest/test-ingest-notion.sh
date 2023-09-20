#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=notion
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

if [ -z "$NOTION_API_KEY" ]; then
   echo "Skipping Notion ingest test because the NOTION_API_KEY env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    notion \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --download-dir "$DOWNLOAD_DIR" \
    --api-key "$NOTION_API_KEY" \
    --output-dir "$OUTPUT_DIR" \
    --database-ids "122b2c22996b435b9de2ee0e9d2b04bc" \
    --num-processes 2 \
    --recursive \
    --verbose


"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
