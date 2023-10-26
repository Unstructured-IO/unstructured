#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-pinecone-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$OPENAI_API_KEY" ] && [ -z "$PINECONE_API_KEY" ]; then
   echo "Skipping Pinecone ingest test because neither OPENAI_API_KEY nor PINECONE_API_KEY env vars are set."
   exit 0
fi

PINECONE_ENVIRONMENT="gcp-starter"
PINECONE_INDEX="ingest-test"
PINECONE_PROJECT_ID="bfa06d5"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {

  # Get response code to check if index exists
  response_code=$(curl \
    -s -o /dev/null \
    -w "%{http_code}" \
    --request GET \
    --url https://controller.$PINECONE_ENVIRONMENT.pinecone.io/databases/$PINECONE_INDEX \
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
    echo "Index $PINECONE_INDEX does not exist, nothing to delete"
  fi

  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT


# Create index
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
  "dimension": 1536,
  "metric": "cosine",
  "pods": 1,
  "replicas": 1,
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
  s3 \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --strategy fast \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
  --anonymous \
  --work-dir "$WORK_DIR" \
  --chunk-elements \
  --chunk-multipage-sections \
  --embedding-api-key "$OPENAI_API_KEY" \
  pinecone \
  --api-key "$PINECONE_API_KEY" \
  --index-name "$PINECONE_INDEX" \
  --environment "$PINECONE_ENVIRONMENT"

sleep 15
num_of_vectors_remote=$(curl --request POST \
     -s \
     --url "https://$PINECONE_INDEX-$PINECONE_PROJECT_ID.svc.$PINECONE_ENVIRONMENT.pinecone.io/describe_index_stats" \
     --header "accept: application/json" \
     --header "content-type: application/json" \
     --header "Api-Key: $PINECONE_API_KEY" | jq -r '.totalVectorCount')

EXPECTED=81
if [ "$num_of_vectors_remote" -ne $EXPECTED ];then
  echo "Number of vectors in Pinecone are $num_of_vectors_remote when the expected number is $EXPECTED. Test failed."
  exit 1
fi
