#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=azure
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

function cleanup() {
  echo "--- Running cleanup ---"

  if [ -d "$OUTPUT_DIR" ]; then
    echo "cleaning up tmp directory: $OUTPUT_DIR"
    rm -rf "$OUTPUT_DIR"
  fi

  echo "--- Cleanup done ---"
}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    azure \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --account-name azureunstructured1 \
    --remote-url abfs://container1/

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
