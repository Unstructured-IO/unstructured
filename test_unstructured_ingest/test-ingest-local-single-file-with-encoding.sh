#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-single-file-with-encoding
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME

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
    local \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --output-dir "$OUTPUT_DIR" \
    --encoding cp1252 \
    --verbose \
    --reprocess \
    --input-path example-docs/fake-html-cp1252.html

set +e

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
