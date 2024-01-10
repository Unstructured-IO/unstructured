#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=weaviate-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  echo "Stopping Weaviate Docker container"
  docker-compose -f scripts/weaviate-test-helpers/docker-compose.yml down --remove-orphans -v

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"

}

trap cleanup EXIT

# Create weaviate instance and create `elements` class
echo "Creating weaviate instance"
# shellcheck source=/dev/null
scripts/weaviate-test-helpers/create-weaviate-instance.sh
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
  weaviate \
  --host-url http://localhost:8080 \
  --class-name elements \
  --anonymous

"$SCRIPT_DIR"/python/test-ingest-weaviate-output.py
