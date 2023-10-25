#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-pinecone-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
PINECONE_INDEX="utic-test-ingest-fixtures-output-$(date +%s)"
# The vector configs on the schema currently only exist on versions:
# 2023-07-01-Preview, 2021-04-30-Preview, 2020-06-30-Preview
API_VERSION=2023-07-01-Preview

if [ -z "$OPENAI_API_KEY" ] && [ -z "$PINECONE_API_KEY" ]; then
   echo "Skipping Pinecone ingest test because neither OPENAI_API_KEY nor PINECONE_API_KEY env vars are set."
   exit 0
fi
# shellcheck disable=SC1091

# --- in progress (to be tested)---
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  response_code=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://controller.$PINECONE_ENVIRONMENT.pinecone.io/databases/$PINECONE_INDEX" \
  --header "Api-Key: $PINECONE_API_KEY" \
  --header 'content-type: application/json')
  if [ "$response_code" == "200" ]; then
    echo "deleting index $DESTINATION_INDEX"
    curl -X DELETE \
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


# --- in progress ---
# Create index
echo "Creating index $PINECONE_INDEX"
# might do it with a curl command as well
python ../scripts/pinecone-test-helpers/create_index.py --index-name "$PINECONE_INDEX"


# if [ "$response_code" -lt 400 ]; then
#   echo "Index creation success: $response_code"
# else
#   echo "Index creation failure: $response_code"
#   exit 1
# fi

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
  --embedding-api-key "$OPENAI_API_KEY" \
  pinecone \
  --api-key "$PINECONE_API_KEY" \
  --index-name "$PINECONE_INDEX" \
  --environment "gcp-starter"

# --- in progress ---
# docs_count_remote=0
# attempt=1
# while [ "$docs_count_remote" -eq 0 ] && [ "$attempt" -lt 6 ]; do
  # echo "attempt $attempt: sleeping 10 seconds to let index finish catching up after writes"
  # sleep 10

  # Check the contents of the index
  # docs_count_remote=$(curl "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX/docs/\$count?api-version=$API_VERSION" \
  #   --header "api-key: $PINECONE_API_KEY" \
  #   --header 'content-type: application/json' | jq)

  # echo "docs count pulled from Pinecone: $docs_count_remote"

  # attempt=$((attempt+1))
done

docs_count_local=0
for i in $(jq length "$OUTPUT_DIR"/**/*.json); do
  docs_count_local=$((docs_count_local+i));
done


if [ "$docs_count_remote" -ne "$docs_count_local" ];then
  echo "Number of docs in Pinecone $docs_count_remote doesn't match the expected docs: $docs_count_local"
  exit 1
fi
