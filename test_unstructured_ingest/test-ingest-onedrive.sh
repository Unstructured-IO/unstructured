#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=onedrive
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$MS_CLIENT_ID" ] || [ -z "$MS_CLIENT_CRED" ] || [ -z "$MS_USER_PNAME" ]; then
   echo "Skipping OneDrive ingest test because the MS_CLIENT_ID, MS_CLIENT_CRED, MS_USER_PNAME env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    onedrive \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --client-cred "$MS_CLIENT_CRED" \
    --client-id "$MS_CLIENT_ID" \
    --tenant "$MS_TENANT_ID" \
    --user-pname "$MS_USER_PNAME" \
    --path '/utic-test-ingest-fixtures' \
    --recursive \

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
