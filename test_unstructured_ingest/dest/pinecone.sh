#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-pinecone-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
writer_processes=$(((max_processes - 1) > 1 ? (max_processes - 1) : 2))

if [ -z "$PINECONE_API_KEY" ]; then
  echo "Skipping Pinecone ingest test because PINECONE_API_KEY env var is not set."
  exit 0
fi

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

# Set the variables with default values if they're not set in the environment
PINECONE_INDEX=${PINECONE_INDEX:-"ingest-test-$RANDOM_SUFFIX"}
PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT:-"us-east1-gcp"}
PINECONE_PROJECT_ID=${PINECONE_PROJECT_ID:-"art8iaj"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {

  # Get response code to check if index exists
  response_code=$(curl \
    -s -o /dev/null \
    -w "%{http_code}" \
    --request GET \
    --url "https://controller.$PINECONE_ENVIRONMENT.pinecone.io/databases/$PINECONE_INDEX" \
    --header 'accept: application/json' \
    --header "Api-Key: $PINECONE_API_KEY")

  # Cleanup (delete) index if it exists
  if [ "$response_code" == "200" ]; then
    echo ""
    echo "deleting index $PINECONE_INDEX"
    curl --request DELETE \
      "https://controller.$PINECONE_ENVIRONMENT.pinecone.io/databases/$PINECONE_INDEX" \
      --header "Api-Key: $PINECONE_API_KEY" \
      --header 'content-type: application/json'

  else
    echo "There was an error during index deletion for index $PINECONE_INDEX, with response code: $response_code. It might be that index $PINECONE_INDEX does not exist, so there is nothing to delete."
  fi

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
}

trap cleanup EXIT

echo "Creating index $PINECONE_INDEX"
response_code=$(curl \
  -s -o /dev/null \
  -w "%{http_code}" \
  --request POST \
  --url "https://controller.$PINECONE_ENVIRONMENT.pinecone.io/databases" \
  --header "accept: text/plain" \
  --header "content-type: application/json" \
  --header "Api-Key: $PINECONE_API_KEY" \
  --data '
{
  "name": "'"$PINECONE_INDEX"'",
  "dimension": 384,
  "metric": "cosine",
  "pods": 1,
  "pod_type": "p1.x1"
}
')

if [ "$response_code" -lt 400 ]; then
  echo "Index creation success: $response_code"
else
  echo "Index creation failure: $response_code"
  exit 1
fi

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
  pinecone \
  --api-key "$PINECONE_API_KEY" \
  --index-name "$PINECONE_INDEX" \
  --environment "$PINECONE_ENVIRONMENT" \
  --batch-size 80 \
  --num-processes "$writer_processes"

# It can take some time for the index to catch up with the content that was written, this check between 10s sleeps
# to give it that time process the writes. Will timeout after checking for a minute.
num_of_vectors_remote=0
attempt=1
sleep_amount=8
while [ "$num_of_vectors_remote" -eq 0 ] && [ "$attempt" -lt 4 ]; do
  echo "attempt $attempt: sleeping $sleep_amount seconds to let index finish catching up after writes"
  sleep $sleep_amount

  num_of_vectors_remote=$(curl --request POST \
    -s \
    --url "https://$PINECONE_INDEX-$PINECONE_PROJECT_ID.svc.$PINECONE_ENVIRONMENT.pinecone.io/describe_index_stats" \
    --header "accept: application/json" \
    --header "content-type: application/json" \
    --header "Api-Key: $PINECONE_API_KEY" | jq -r '.totalVectorCount')

  echo "vector count in Pinecone: $num_of_vectors_remote"
  attempt=$((attempt + 1))
done

EXPECTED=1404

if [ "$num_of_vectors_remote" -ne $EXPECTED ]; then
  echo "Number of vectors in Pinecone are $num_of_vectors_remote when the expected number is $EXPECTED. Test failed."
  exit 1
fi
