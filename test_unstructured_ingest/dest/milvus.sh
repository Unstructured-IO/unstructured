#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=milvus-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  echo "Stopping Milvus Docker container"
  docker compose -f scripts/milvus-test-helpers/docker-compose.yml down --remove-orphans -v

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"

}

trap cleanup EXIT

DB_NAME=ingest_test_db
HOST="localhost"
PORT=19530
MILVUS_URI="http://${HOST}:${PORT}"
COLLECTION_NAME="ingest_test"

# check for pymilvus
pip freeze
# Create milvus instance
echo "Creating milvus instance"
# shellcheck source=/dev/null
docker compose -f scripts/milvus-test-helpers/docker-compose.yml up -d --wait-timeout 60
python scripts/milvus-test-helpers/create_collection.py --db-name $DB_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --work-dir "$WORK_DIR" \
  --embedding-provider "langchain-huggingface" \
  milvus \
  --uri $MILVUS_URI \
  --db-name $DB_NAME \
  --collection-name $COLLECTION_NAME

sample_embeddings=$(cat "$WORK_DIR"/upload_stage/* | jq '.[0].embeddings')
expected_count=$(cat "$WORK_DIR"/upload_stage/* | jq 'length')

./scripts/milvus-test-helpers/test_outputs.py \
  --db-name $DB_NAME \
  --embeddings "$sample_embeddings" \
  --collection-name $COLLECTION_NAME \
  --count "$expected_count"
