#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=singlestore-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  echo "Stopping Singlestore Docker container"
  docker compose -f scripts/singlestore-test-helpers/docker-compose.yml down --remove-orphans -v

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"

}

trap cleanup EXIT

# Create singlestore instance and create `elements` class
echo "Creating singlestore instance"
# shellcheck source=/dev/null
docker compose -f scripts/singlestore-test-helpers/docker-compose.yml up -d --wait-timeout 60

DATABASE=ingest_test
USER=root
HOST=localhost
PASSWORD=password
PORT=3306
TABLE=elements

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
  singlestore \
  --host $HOST \
  --user $USER \
  --password $PASSWORD \
  --database $DATABASE \
  --port $PORT \
  --table-name $TABLE \
  --drop-empty-cols

expected_num_elements=$(cat $WORK_DIR/embed/* | jq 'length')
./scripts/singlestore-test-helpers/test_outputs.py --table-name $TABLE --database $DATABASE --num-elements $expected_num_elements
