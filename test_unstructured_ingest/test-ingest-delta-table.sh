#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=delta-table
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
   echo "aws credentials not found as env vars"
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    delta-table \
    --download-dir "$DOWNLOAD_DIR" \
    --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
    --structured-output-dir "$OUTPUT_DIR" \
    --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    --preserve-downloads \
    --verbose

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
