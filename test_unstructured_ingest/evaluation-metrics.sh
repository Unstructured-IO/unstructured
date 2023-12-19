#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# List all structured outputs to use in this evaluation
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output-eval
mkdir -p "$OUTPUT_DIR"

EVAL_NAME="$1"

if [ "$EVAL_NAME" == "text-extraction" ]; then
  METRIC_STRATEGY="measure-text-extraction-accuracy-command"
elif [ "$EVAL_NAME" == "element-type" ]; then
  METRIC_STRATEGY="measure-element-type-accuracy-command"
else
  echo "Wrong metric evaluation strategy given. Expected one of [ text-extraction, element-type ]. Got [ $EVAL_NAME ]."
  exit 1
fi

# Download cct test from s3
BUCKET_NAME=utic-dev-tech-fixtures
FOLDER_NAME=small-eval-"$EVAL_NAME"
SOURCE_DIR=$OUTPUT_ROOT/gold-standard/$FOLDER_NAME
mkdir -p "$SOURCE_DIR"
aws s3 cp "s3://$BUCKET_NAME/$FOLDER_NAME" "$SOURCE_DIR" --recursive --no-sign-request --region us-east-2

EXPORT_DIR=$OUTPUT_ROOT/metrics-tmp/$EVAL_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
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
)

read -ra output_args <<<"$(generate_args "output" "$OUTPUT_DIR" "${OUTPUT_LIST[@]}")"
read -ra source_args <<<"$(generate_args "source" "$SOURCE_DIR" "${SOURCE_LIST[@]}")"

# mkdir export_dir is handled in python script
PYTHONPATH=. ./unstructured/ingest/evaluate.py \
  $METRIC_STRATEGY "${output_args[@]}" "${source_args[@]}" \
  --export_dir "$EXPORT_DIR"

"$SCRIPT_DIR"/check-diff-evaluation-metrics.sh "$EVAL_NAME"
