#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

sh "$SCRIPT_DIR"/check-num-files-expected-output.sh 3 $OUTPUT_FOLDER_NAME 20k

PYTHONPATH=. ./unstructured/ingest/main.py \
    s3 \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
    --anonymous


sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
