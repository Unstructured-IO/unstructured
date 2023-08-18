#!/usr/bin/env bash

# Set either BOX_APP_CONFIG (app config json content as string) or
# BOX_APP_CONFIG_PATH (path to app config json file) env var

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=box
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$BOX_APP_CONFIG" ] && [ -z "$BOX_APP_CONFIG_PATH" ]; then
   echo "Skipping Box ingest test because neither BOX_APP_CONFIG nor BOX_APP_CONFIG_PATH env vars are set."
   exit 0
fi

if [ -z "$BOX_APP_CONFIG_PATH" ]; then
    # Create temporary service key file
    BOX_APP_CONFIG_PATH=$(mktemp)
    echo "$BOX_APP_CONFIG" >"$BOX_APP_CONFIG_PATH"
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    box \
    --download-dir "$DOWNLOAD_DIR" \
    --box-app-config "$BOX_APP_CONFIG_PATH" \
    --remote-url box://utic-test-ingest-fixtures \
    --structured-output-dir box-output \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --num-processes 2 \
    --preserve-downloads \
    --recursive \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME