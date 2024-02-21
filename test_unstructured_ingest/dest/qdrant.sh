#!/bin/bash

set -ex

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=qdrant-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
writer_processes=$(((max_processes - 1) > 1 ? (max_processes - 1) : 2))
CONTAINTER_NAME="qdrant_test"
QDRANT_PORT=6333
QDRANT_HOST=localhost:$QDRANT_PORT
COLLECTION_NAME="qdrant-test-$(date +%s)"
EXPECTED_POINTS_COUNT=1404
RETRIES=5

function stop_docker() {
  docker stop $CONTAINTER_NAME
}

docker run -d --rm \
  -p 6333:$QDRANT_PORT \
  --name $CONTAINTER_NAME qdrant/qdrant:latest

trap stop_docker SIGINT
trap stop_docker ERR

until curl --output /dev/null --silent --get --fail http://$QDRANT_HOST/collections; do
  RETRIES=$((RETRIES - 1))
  if [ "$RETRIES" -le 0 ]; then
    echo "Qdrant server failed to start"
    stop_docker
    exit 1
  fi
  printf 'Waiting for Qdrant server to start...'
  sleep 5
done

curl -X PUT \
  http://$QDRANT_HOST/collections/"$COLLECTION_NAME" \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
}'

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --work-dir "$WORK_DIR" \
  --chunk-elements \
  --chunk-combine-text-under-n-chars 200 --chunk-new-after-n-chars 2500 --chunk-max-characters 38000 --chunk-multipage-sections \
  --embedding-provider "langchain-huggingface" \
  qdrant \
  --collection-name "$COLLECTION_NAME" \
  --location "http://"$QDRANT_HOST \
  --batch-size 80 \
  --num-processes "$writer_processes"

response=$(curl -s -X POST \
  $QDRANT_HOST/collections/"$COLLECTION_NAME"/points/count \
  -H 'Content-Type: application/json' \
  -d '{
     "exact": true
}')

count=$(echo "$response" | jq -r '.result.count')

if [ "$count" -ne $EXPECTED_POINTS_COUNT ]; then
  echo "Points count assertion failed. Expected: $EXPECTED. Got: $count. Test failed."
  stop_docker
  exit 1
fi

stop_docker
