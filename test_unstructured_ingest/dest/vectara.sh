#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-vectara-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))
CORPUS_NAME="test-corpus-vectara-"$RANDOM_SUFFIX

# Expected size of the uploaded document
EXPECTED_CORPUS_SIZE=8829936

if [ -z "$VECTARA_OAUTH_CLIENT_ID" ] && [ -z "$VECTARA_OAUTH_SECRET" ] && [ -z "$VECTARA_CUSTOMER_ID" ]; then
  echo "Skipping VECTARA ingest test because VECTARA_OAUTH_CLIENT_ID, VECTARA_OAUTH_SECRET, or VECTARA_CUSTOMER_ID env var is not set."
  exit 8
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  echo "Deleting corpus $corpus_id ($CORPUS_NAME)"
  curl -sS -L -X POST 'https://api.vectara.io/v1/delete-corpus' \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    -H "Authorization: Bearer $access_token" \
    -H "customer-id: $VECTARA_CUSTOMER_ID" \
    --data-raw "{
    \"corpusId\": $corpus_id
    }"

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
  --customer-id "$VECTARA_CUSTOMER_ID" \
  --oauth-client-id "$VECTARA_OAUTH_CLIENT_ID" \
  --oauth-secret "$VECTARA_OAUTH_SECRET" \
  --corpus-name "$CORPUS_NAME"

# Get JWT token
jwt_token_resp=$(curl -sS -XPOST -H "Content-type: application/x-www-form-urlencoded" -d \
  "grant_type=client_credentials&client_id=$VECTARA_OAUTH_CLIENT_ID&client_secret=$VECTARA_OAUTH_SECRET" \
  "https://vectara-prod-$VECTARA_CUSTOMER_ID.auth.us-west-2.amazoncognito.com/oauth2/token")
access_token=$(echo "$jwt_token_resp" | jq -r '.access_token')

# Get corpus ID from name
corpora_resp=$(curl -sS -L -X POST 'https://api.vectara.io/v1/list-corpora' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "customer-id: $VECTARA_CUSTOMER_ID" \
  -H "Authorization: Bearer $access_token" \
  --data-raw "{
                    \"numResults\": 100,
                    \"filter\": \"$CORPUS_NAME\"
                    }")
corpus_id=$(echo "$corpora_resp" | jq -r '.corpus[0].id')

# Check that the size of the corpus is as expected
get_corpus_size=$(curl -L -X POST 'https://api.vectara.io/v1/compute-corpus-size' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "customer-id: $VECTARA_CUSTOMER_ID" \
  -H "Authorization: Bearer $access_token" \
  --data-raw "{
  \"corpusId\": $corpus_id
}")
corpus_size=$(echo "$get_corpus_size" | jq -r '.size.size')

if [ "$corpus_size" == "$EXPECTED_CORPUS_SIZE" ]; then
  echo "Corpus size is as expected: $corpus_size"
else
  echo "Corpus size is not as expected: $corpus_size"
  exit 1
fi
