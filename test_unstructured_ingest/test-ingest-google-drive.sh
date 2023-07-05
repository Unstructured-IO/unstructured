#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=google-drive
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
    echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
    echo "The Google Drive test content can be found at https://drive.google.com/drive/folders/1OQZ66OHBE30rNsNa7dweGLfRmXvkT_jr"
    exit 0
fi

# Create temporary service key file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
echo "$GCP_INGEST_SERVICE_KEY" >"$GCP_INGEST_SERVICE_KEY_FILE"

PYTHONPATH=. unstructured/ingest/main.py \
    --download-dir "$DOWNLOAD_DIR" \
    --drive-id 1OQZ66OHBE30rNsNa7dweGLfRmXvkT_jr \
    --drive-service-account-key "$GCP_INGEST_SERVICE_KEY_FILE" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
