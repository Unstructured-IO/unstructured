#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=delta-table-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DESTINATION_TABLE=$SCRIPT_DIR/delta-table-dest
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  cleanup_dir "$DESTINATION_TABLE"
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}

trap cleanup EXIT

# Make sure directory doesn't exist at the beginning of script as this will cause it to break
if [ -d "$DESTINATION_TABLE" ]; then
  echo "cleaning up directory: $DESTINATION_TABLE"
  rm -rf "$DESTINATION_TABLE"
else
  echo "$DESTINATION_TABLE does not exist or is not a directory, skipping deletion"
fi

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
  --table-uri "$DESTINATION_TABLE"

python "$SCRIPT_DIR"/python/test-ingest-delta-table-output.py --table-uri "$DESTINATION_TABLE"
