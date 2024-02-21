#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=sql-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}
DATABASE_TYPE="pgvector"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  echo "Stopping SQL DB Docker container"
  docker-compose -f scripts/sql-test-helpers/docker-compose-"$DATABASE_TYPE".yaml down --remove-orphans -v
  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

# Create sql instance and create `elements` class
echo "Creating SQL DB instance"
# shellcheck source=/dev/null
scripts/sql-test-helpers/create-sql-instance.sh "$DATABASE_TYPE"
wait

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --input-path example-docs/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  --embedding-provider "langchain-huggingface" \
  sql \
  --db-type "postgresql" \
  --username unstructured \
  --password test \
  --host localhost \
  --port 5433 \
  --database elements

"$SCRIPT_DIR"/python/test-ingest-sql-output.py "$DATABASE_TYPE" "5433"
