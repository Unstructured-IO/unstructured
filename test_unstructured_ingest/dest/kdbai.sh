#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=kdbai-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# Check if KDBAI_API_KEY & KDBAI_ENDPOINT is set
if [ -z "$KDBAI_API_KEY" ] && [ -z "$KDBAI_ENDPOINT" ]; then
  echo "Skipping KDBAI ingest test because KDBAI_API_KEY or KDBAI_ENDPOINT env vars is not set."
  exit 0
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {

  # Drop test table 
  echo "Drop kdbai table"
  python scripts/kdbai-test-helpers/manage_table.py \
   --op dropTable
        
  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"

}

trap cleanup EXIT
wait 

# Connect to kdbai and create table
echo "Connecting to kdbai table"
# shellcheck source=/dev/null
python scripts/kdbai-test-helpers/manage_table.py \
    --op createTable
wait

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  --embedding-provider "langchain-huggingface" \
  kdbai \
  --endpoint "$KDBAI_ENDPOINT" \
  --api-key "$KDBAI_API_KEY" \
  --table-name "unstructured_test" \
  --batch-size 100

python "$SCRIPT_DIR"/python/test-kdbai-output.py
