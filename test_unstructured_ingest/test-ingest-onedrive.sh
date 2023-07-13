#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=onedrive
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$MS_CLIENT_ID" ] || [ -z "$MS_CLIENT_CRED" ]; then
   echo "Skipping OneDrive ingest test because the MS_CLIENT_ID or MS_CLIENT_CRED env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --download-dir "$DOWNLOAD_DIR" \
    --ms-client-cred "$MS_CLIENT_CRED" \
    --ms-client-id "$MS_CLIENT_ID" \
    --ms-tenant "3d60a7e5-1e32-414e-839b-1c6e6782613d" \
    --ms-user-pname "devops@unstructuredio.onmicrosoft.com" \
    --ms-onedrive-folder '/utic-test-ingest-fixtures' \
    --metadata-exclude file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --recursive \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME