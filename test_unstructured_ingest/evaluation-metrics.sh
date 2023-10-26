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
SOURCE_DIR=$SCRIPT_DIR/gold-standard/$FOLDER_NAME
mkdir -p "$SOURCE_DIR"
# aws s3 cp "s3://$BUCKET_NAME/$FOLDER_NAME" "$SOURCE_DIR" --recursive --no-sign-request --region us-east-2

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$SOURCE_DIR"
}
trap cleanup EXIT

# build args
function generate_args() {
  local argtype="$1"
  local dirpath="$2"
  local list=("${@:3}")

  local -a args

  args=("--${argtype}_dir" "$dirpath")
  for filename in "${list[@]}"; do
      args+=("--${argtype}_list" "$filename")
  done
  echo "${args[@]}"
}

# List selected output as a subset of OUTPUT_DIR, if any
OUTPUT_LIST=(
)
# List selected source as a subset of SOURCE_DIR, if any
SOURCE_LIST=(
'IRS-form-1987.pdf.txt'
'handbook-1p.docx.txt'
)

EXPORT_DIR="$SCRIPT_DIR"/metrics

output_args=($(generate_args "output" "$OUTPUT_DIR" "${OUTPUT_LIST[@]}"))
source_args=($(generate_args "source" "$SOURCE_DIR" "${SOURCE_LIST[@]}"))

PYTHONPATH=. ./unstructured/ingest/evaluate.py \
    measure-text-edit-distance \
    "${output_args[@]}" \
    "${source_args[@]}" \
    --export_dir "$EXPORT_DIR"

# ELEMENT_TYPE_DIR="$SCRIPT_DIR"/expected-structured-output
# PYTHONPATH=. ./unstructured/ingest/evaluate.py \
#     measure-element-type-accuracy \
#     --output_dir "$OUTPUT_DIR" \
#     --source_dir "$ELEMENT_TYPE_DIR" \
#     --export_dir "$EXPORT_DIR"