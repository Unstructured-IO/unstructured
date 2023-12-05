#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=azure-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

if [ -z "$AZURE_DEST_CONNECTION_STR" ]; then
  echo "Skipping Azure destination ingest test because the AZURE_DEST_CONNECTION_STR env var is not set."
  exit 8
fi

CONTAINER=utic-ingest-test-fixtures-output
DIRECTORY=$(uuidgen)
REMOTE_URL_RAW="$CONTAINER/$DIRECTORY/"
REMOTE_URL="abfs://$REMOTE_URL_RAW"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  python "$SCRIPT_DIR"/python/test-azure-output.py down \
    --connection-string "$AZURE_DEST_CONNECTION_STR" \
    --container "$CONTAINER" \
    --blob-path "$DIRECTORY"

}
trap cleanup EXIT

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
  azure \
  --overwrite \
  --remote-url "$REMOTE_URL" \
  --connection-string "$AZURE_DEST_CONNECTION_STR"

# Simply check the number of files uploaded
python "$SCRIPT_DIR"/python/test-azure-output.py check \
  --expected-files 1 \
  --connection-string "$AZURE_DEST_CONNECTION_STR" \
  --container "$CONTAINER" \
  --blob-path "$DIRECTORY"
