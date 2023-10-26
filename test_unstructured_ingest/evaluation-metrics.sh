#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# List all structured outputs to use in this evaluation
OUTPUT_DIR=$SCRIPT_DIR/structured-output-eval
mkdir -p "$OUTPUT_DIR"

# Download cct test from s3
BUCKET_NAME=utic-dev-tech-fixtures
FOLDER_NAME=small-cct
CCT_DIR=$SCRIPT_DIR/gold-standard/$FOLDER_NAME
mkdir -p "$CCT_DIR"
aws s3 cp "s3://$BUCKET_NAME/$FOLDER_NAME" "$CCT_DIR" --recursive --no-sign-request --region us-east-2

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$CCT_DIR"
}
trap cleanup EXIT

EXPORT_DIR="$SCRIPT_DIR"/metrics
PYTHONPATH=. ./unstructured/ingest/evaluate.py \
    --output_dir "$OUTPUT_DIR" \
    --source_dir "$CCT_DIR" \
    --export_dir "$EXPORT_DIR"
