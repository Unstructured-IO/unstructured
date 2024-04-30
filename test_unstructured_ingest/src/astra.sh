#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=astra-src
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

if [ -z "$ASTRA_DB_TOKEN" ]; then
  echo "Skipping Astra DB ingest test because ASTRA_DB_TOKEN env var is not set."
  exit 0
fi

if [ -z "$ASTRA_DB_ENDPOINT" ]; then
  echo "Skipping Astra DB ingest test because ASTRA_DB_ENDPOINT env var is not set."
  exit 0
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))
COLLECTION_NAME="astra_test_output_$RANDOM_SUFFIX"
EMBEDDING_DIMENSION=384

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  astra \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --token "$ASTRA_DB_TOKEN" \
  --api-endpoint "$ASTRA_DB_ENDPOINT" \
  --collection-name "ingest_test_collection" \
  --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
