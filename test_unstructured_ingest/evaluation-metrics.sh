#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# List all structured outputs to use in this evaluation
OUTPUT_DIR=$SCRIPT_DIR/structured-output
structured_outputs=(
'box/handbook-1p.docx.json'
)

# Download cct test from s3
BUCKET_NAME=utic-dev-tech-fixtures
FOLDER_NAME=small-cct
CCT_DIR=$SCRIPT_DIR/gold-standard/$FOLDER_NAME
aws s3 cp "s3://$BUCKET_NAME/$FOLDER_NAME" "$CCT_DIR" --recursive --no-sign-request --debug

PYTHONPATH=. ./unstructured/ingest/evaluate.py \
    --output_dir "$OUTPUT_DIR" \
    --output_list "${structured_outputs[@]}" \
    --source_dir "$CCT_DIR" 