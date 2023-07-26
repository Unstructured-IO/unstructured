#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=slack
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME


PYTHONPATH=. ./unstructured/ingest/main.py \
   --download-dir "$DOWNLOAD_DIR" \
   --metadata-exclude coordinates,file_directory,metadata.data_source.date_processed,metadata.date \
   --partition-strategy hi_res \
   --preserve-downloads \
   --reprocess \
   --structured-output-dir "$OUTPUT_DIR" \
   --verbose \
   slack \
   --channels C052BGT7718 \
   --token "${SLACK_TOKEN}" \
   --start-date 2023-04-01 \
   --end-date 2023-04-08T12:00:00-08:00

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
