#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=Sharepoint
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$SHAREPOINT_CLIENT_ID" ] || [ -z "$SHAREPOINT_CRED" ]; then
   echo "Skipping Sharepoint ingest test because the MS_CLIENT_ID or MS_CLIENT_CRED env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --ms-sharepoint-client-id "$SHAREPOINT_CLIENT_ID" \
    --ms-sharepoint-client-cred "$SHAREPOINT_CRED" \
    --ms-sharepoint-site "$SHAREPOINT_SITE" \
    --ms-sharepoint-folder "Shared Documents" \
    --ms-sharepoint-pages \
    --metadata-exclude file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --recursive \
    --reprocess \
    --download-dir "$DOWNLOAD_DIR" \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME