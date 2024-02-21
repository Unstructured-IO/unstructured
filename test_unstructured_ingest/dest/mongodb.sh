#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=mongodb-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_MONGO_COLLECTION="utic-test-ingest-fixtures-output-$(uuidgen)"
CI=${CI:-"false"}

if [ -z "$MONGODB_URI" ] && [ -z "$MONGODB_DATABASE_NAME" ]; then
  echo "Skipping MongoDB destination ingest test because the MONGODB_URI and MONGODB_DATABASE_NAME env var are not set."
  exit 8
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  python "$SCRIPT_DIR"/python/test-ingest-mongodb.py \
    --uri "$MONGODB_URI" \
    --database "$MONGODB_DATABASE_NAME" \
    --collection "$DESTINATION_MONGO_COLLECTION" down

}

trap cleanup EXIT

python "$SCRIPT_DIR"/python/test-ingest-mongodb.py \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$DESTINATION_MONGO_COLLECTION" up

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  --embedding-provider "langchain-huggingface" \
  mongodb \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$DESTINATION_MONGO_COLLECTION"

python "$SCRIPT_DIR"/python/test-ingest-mongodb.py \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$DESTINATION_MONGO_COLLECTION" \
  check --expected-records 5

python "$SCRIPT_DIR"/python/test-ingest-mongodb.py \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$DESTINATION_MONGO_COLLECTION" \
  check-vector \
  --output-json "$OUTPUT_ROOT"/structured-output/$OUTPUT_FOLDER_NAME/fake-memo.pdf.json
