#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=astra-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

if [ -z "$ASTRA_DB_TOKEN" ]; then
  echo "Skipping Astra DB ingest test because ASTRA_DB_TOKEN env var is not set."
  exit 0
fi

if [ -z "$ASTRA_DB_ENDPOINT" ]; then
  echo "Skipping Astra DB ingest test because ASTRA_DB_ENDPOINT env var is not set."
  exit 0
fi

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))
COLLECTION_NAME="astra_test_output_$RANDOM_SUFFIX"
EMBEDDING_DIMENSION=384

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  python "$SCRIPT_DIR"/python/test-ingest-astra-output.py \
    --token "$ASTRA_DB_TOKEN" \
    --api-endpoint "$ASTRA_DB_ENDPOINT" \
    --collection-name "$COLLECTION_NAME" down
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
  --chunk-elements \
  --chunk-max-characters 1500 \
  --chunk-multipage-sections \
  --embedding-provider "langchain-huggingface" \
  astra \
  --token "$ASTRA_DB_TOKEN" \
  --api-endpoint "$ASTRA_DB_ENDPOINT" \
  --collection-name "$COLLECTION_NAME" \
  --embedding-dimension "$EMBEDDING_DIMENSION" \
  --requested-indexing-policy '{"deny": ["metadata"]}'

python "$SCRIPT_DIR"/python/test-ingest-astra-output.py \
  --token "$ASTRA_DB_TOKEN" \
  --api-endpoint "$ASTRA_DB_ENDPOINT" \
  --collection-name "$COLLECTION_NAME" check
