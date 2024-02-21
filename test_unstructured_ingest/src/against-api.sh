#!/usr/bin/env bash

set -e

if [ -z "$UNS_API_KEY" ]; then
  echo "Skipping ingest test against api because the UNS_API_KEY env var is not set."
  exit 8
fi
SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=api-ingest-output
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

TEST_FILE_NAME=layout-parser-paper-with-table.pdf

# including pdf-infer-table-structure to validate partition arguments are passed to the api
RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --api-key "$UNS_API_KEY" \
  --metadata-exclude coordinates,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --partition-by-api \
  --strategy hi_res \
  --pdf-infer-table-structure \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --num-processes "$max_processes" \
  --input-path "example-docs/$TEST_FILE_NAME" \
  --work-dir "$WORK_DIR"

RESULT_FILE_PATH="$OUTPUT_DIR/$TEST_FILE_NAME.json"
# validate that there is at least one table with text_as_html in the results
if [ "$(jq 'any(.[]; .metadata.text_as_html != null)' "$RESULT_FILE_PATH")" = "false" ]; then
  echo "No table with text_as_html found in $RESULT_FILE_PATH but at least one was expected."
  exit 1
fi
