#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=outlook
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

if [ -z "$MS_CLIENT_ID" ] || [ -z "$MS_CLIENT_CRED" ] || [ -z "$MS_TENANT_ID" ] || [ -z "$MS_USER_EMAIL" ]; then
   echo "Skipping Outlook ingest test because the MS_CLIENT_ID or MS_CLIENT_CRED or MS_TENANT_ID or MS_USER_EMAIL env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    outlook \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --client-cred "$MS_CLIENT_CRED" \
    --client-id "$MS_CLIENT_ID" \
    --tenant "$MS_TENANT_ID" \
    --user-email "$MS_USER_EMAIL" \
    --outlook-folders IntegrationTest \
    --recursive



sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
