#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=couchbase-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_PATH=$SCRIPT_DIR/couchbase-dest
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  # Kill couchbase background process
  pgrep -f couchbase-dest | xargs kill
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
  --input-path example-docs/book-war-and-peace-1p.txt \
  --work-dir "$WORK_DIR" \
  --chunking-strategy by_title \
  --chunk-max-characters 1500 \
  --chunk-multipage-sections \
  --embedding-provider "langchain-huggingface" \
  couchbase \
  --connection-string "couchbases://cb.kdhjgj-a-szlcqfw.customsubdomain.nonprod-project-avengers.com?tls_verify=none" \
  --bucket "pdf-docs" \
  --username "Lokesh" \
  --password "Lokesh@123" \
  --scope "shared" \
  --collection "docs" \
  --search-index "pdf-search" \
  --batch-size 80

#python "$SCRIPT_DIR"/python/test-ingest-couchbase-output.py --collection-name "$COLLECTION_NAME"
