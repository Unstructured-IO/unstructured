#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=delta-table-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_TABLE=$OUTPUT_ROOT/delta-table-dest
CI=${CI:-"false"}

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
    echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
    exit 0
fi

# Create temporary service key file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
echo "$GCP_INGEST_SERVICE_KEY" > "$GCP_INGEST_SERVICE_KEY_FILE"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$DESTINATION_TABLE"
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
    --reprocess \
    --input-path example-docs/fake-memo.pdf \
    --work-dir "$WORK_DIR" \
    delta-table \
    --table-uri "$DESTINATION_TABLE" \
    --drop-empty-cols

python "$SCRIPT_DIR"/python/test-ingest-delta-table-output.py --table-uri "$DESTINATION_TABLE"
