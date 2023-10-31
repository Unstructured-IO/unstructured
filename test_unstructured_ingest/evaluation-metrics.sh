#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# List all structured outputs to use in this evaluation
OUTPUT_DIR=$SCRIPT_DIR/structured-output-eval
mkdir -p "$OUTPUT_DIR"

EVAL_NAME="$1"

# Download cct test from s3
BUCKET_NAME=utic-dev-tech-fixtures
FOLDER_NAME=small-eval-"$EVAL_NAME"
LOCAL_EVAL_SOURCE_DIR=$SCRIPT_DIR/gold-standard/$FOLDER_NAME
mkdir -p "$LOCAL_EVAL_SOURCE_DIR"
aws s3 cp "s3://$BUCKET_NAME/$FOLDER_NAME" "$LOCAL_EVAL_SOURCE_DIR" --recursive --no-sign-request --region us-east-2

EXPORT_DIR="$SCRIPT_DIR"/metrics

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$LOCAL_EVAL_SOURCE_DIR"
}
trap cleanup EXIT

if [ "$EVAL_NAME" == "text-extraction" ]; then
  STRATEGY="measure-text-edit-distance"
elif [ "$EVAL_NAME" == "element-type" ]; then
  STRATEGY="measure-element-type-accuracy"
else
  echo "Wrong evaluation strategy given. Got [ $EVAL_NAME ]."
  exit 1
fi

PYTHONPATH=. ./unstructured/ingest/evaluate.py \
    $STRATEGY \
    --output_dir "$OUTPUT_DIR" \
    --source_dir "$LOCAL_EVAL_SOURCE_DIR" \
    --export_dir "$EXPORT_DIR"