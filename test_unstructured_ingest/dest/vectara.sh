#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-vectara-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

if [ -z "$VECTARA_API_KEY" ]; then
  echo "Skipping VECTARA ingest test because VECTARA_API_KEY env var is not set."
  exit 0
fi
if [ -z "$VECTARA_CUSTOMER_ID" ]; then
  echo "Skipping VECTARA ingest test because VECTARA_CUSTOMER_ID env var is not set."
  exit 0
fi
if [ -z "$VECTARA_CORPUS_ID" ]; then
  echo "Skipping VECTARA ingest test because VECTARA_CORPUS_ID env var is not set."
  exit 0
fi


RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {

  # Get response code to check if index exists
  response_code=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H 'Content-Type: application/json' \
    -H "x-api-key: $VECTARA_API_KEY" \
    -H "customer-id: $VECTARA_CUSTOMER_ID" \
    'https://api.vectara.io/v1/query' \
    --data-raw "{
      \"query\": [
        {
          \"query\": \"What is the answer to the life, the universe, and everything?\",
          \"start\": 0,
          \"numResults\": 10,
          \"corpusKey\": [
            {
              \"customerId\": $VECTARA_CUSTOMER_ID,
              \"corpusId\": $VECTARA_CORPUS_ID
            }
          ]
        }
      ]
    }")

  if [ "$response_code" == "200" ]; then
    echo "VECTARA Corpus check okay."
  else
    echo "There was an error during CORPUS check."
  fi

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --work-dir "$WORK_DIR" \
  vectara \
  --api-key "$VECTARA_API_KEY" \
  --corpus-id "$VECTARA_CORPUS_ID" \
  --customer-id "$VECTARA_CUSTOMER_ID" \
