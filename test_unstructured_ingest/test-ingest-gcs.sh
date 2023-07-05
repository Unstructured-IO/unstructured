#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=gcs
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
    echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
    exit 0
fi

# Create temporary service key file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
echo "$GCP_INGEST_SERVICE_KEY" >"$GCP_INGEST_SERVICE_KEY_FILE"

PYTHONPATH=. ./unstructured/ingest/main.py \
    --download-dir "$DOWNLOAD_DIR" \
    --gcs-token "$GCP_INGEST_SERVICE_KEY_FILE" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed \
    --preserve-downloads \
    --recursive \
    --remote-url gs://utic-test-ingest-fixtures/ \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
