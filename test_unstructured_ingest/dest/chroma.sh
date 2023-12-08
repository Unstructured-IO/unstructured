#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=chroma-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_PATH=$SCRIPT_DIR/chroma-dest
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
writer_processes=$(( (max_processes - 1) > 1 ? (max_processes - 1) : 2 ))
CI=${CI:-"false"}

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

COLLECTION_NAME="chroma-test-output-$RANDOM_SUFFIX"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  cleanup_dir "$DESTINATION_PATH"
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --work-dir "$WORK_DIR" \
  --chunk-elements \
  --chunk-multipage-sections \
  --embedding-provider "langchain-huggingface" \
  chroma \
  --db-path "$DESTINATION_PATH" \
  --collection-name "$COLLECTION_NAME" \
  --batch-size 80

python "$SCRIPT_DIR"/python/test-ingest-chroma-output.py --db-path "$DESTINATION_PATH" --collection-name "$COLLECTION_NAME"

