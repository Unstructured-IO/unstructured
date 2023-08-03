#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=wikipedia
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    wikipedia \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --page-title "Open Source Software"

sh "$SCRIPT_DIR"/check-num-files-output.sh 3 $OUTPUT_FOLDER_NAME
