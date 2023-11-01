#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-azure-cog-search-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_INDEX="utic-test-ingest-fixtures-output-$(date +%s)"
# The vector configs on the schema currently only exist on versions:
# 2023-07-01-Preview, 2021-04-30-Preview, 2020-06-30-Preview
API_VERSION=2023-07-01-Preview

if [ -z "$AZURE_SEARCH_ENDPOINT" ] && [ -z "$AZURE_SEARCH_API_KEY" ]; then
   echo "Skipping Azure Cognitive Search ingest test because neither AZURE_SEARCH_ENDPOINT nor AZURE_SEARCH_API_KEY env vars are set."
   exit 0
fi
# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  response_code=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
  --header "api-key: $AZURE_SEARCH_API_KEY" \
  --header 'content-type: application/json')
  if [ "$response_code" == "200" ]; then
    echo "deleting index $DESTINATION_INDEX"
    curl -X DELETE \
    "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
    --header "api-key: $AZURE_SEARCH_API_KEY" \
    --header 'content-type: application/json'
  else
    echo "Index $DESTINATION_INDEX does not exist, nothing to delete"
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
echo "Creating index $DESTINATION_INDEX"
response_code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
"https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
--header "api-key: $AZURE_SEARCH_API_KEY" \
--header 'content-type: application/json' \
--data "@$SCRIPT_DIR/files/azure_cognitive_index_schema.json")

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
  azure-cognitive-search \
  --key "$AZURE_SEARCH_API_KEY" \
  --endpoint "$AZURE_SEARCH_ENDPOINT" \
  --index "$DESTINATION_INDEX"


# It can take some time for the index to catch up with the content that was written, this check between 10s sleeps
# to give it that time process the writes. Will timeout after checking for a minute.
docs_count_remote=0
attempt=1
while [ "$docs_count_remote" -eq 0 ] && [ "$attempt" -lt 6 ]; do
  echo "attempt $attempt: sleeping 10 seconds to let index finish catching up after writes"
  sleep 10

  # Check the contents of the index
  docs_count_remote=$(curl "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX/docs/\$count?api-version=$API_VERSION" \
    --header "api-key: $AZURE_SEARCH_API_KEY" \
    --header 'content-type: application/json' | jq)

  echo "docs count pulled from Azure: $docs_count_remote"

  attempt=$((attempt+1))
done


docs_count_local=0
for i in $(jq length "$OUTPUT_DIR"/**/*.json); do
  docs_count_local=$((docs_count_local+i));
done


if [ "$docs_count_remote" -ne "$docs_count_local" ];then
  echo "Number of docs in Azure $docs_count_remote doesn't match the expected docs: $docs_count_local"
  exit 1
fi
