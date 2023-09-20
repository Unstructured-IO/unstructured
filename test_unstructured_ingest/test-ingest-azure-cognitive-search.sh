#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_INDEX="utic-test-ingest-fixtures-output-$(date +%s)"
API_VERSION=2020-06-30

if [ -z "$AZURE_SEARCH_ENDPOINT" ] && [ -z "$AZURE_SEARCH_API_KEY" ]; then
   echo "Skipping Azure Cognitive Search ingest test because neither AZURE_SEARCH_ENDPOINT nor AZURE_SEARCH_API_KEY env vars are set."
   exit 0
fi

function cleanup {
  response_code=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
  --header "api-key: JV1LDVRivKEY9J9rHBQqQeTvaGoYbD670RWRaANxaTAzSeDy8Eon" \
  --header 'content-type: application/json')
  if [ "$response_code" == "200" ]; then
    echo "deleting index $DESTINATION_INDEX"
    curl -X DELETE \
    "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
    --header "api-key: JV1LDVRivKEY9J9rHBQqQeTvaGoYbD670RWRaANxaTAzSeDy8Eon" \
    --header 'content-type: application/json'
  else
    echo "Index $DESTINATION_INDEX does not exist, nothing to delete"
  fi
}

trap cleanup EXIT


# Create index
echo "Creating index $DESTINATION_INDEX"
response_code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
"https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX?api-version=$API_VERSION" \
--header "api-key: JV1LDVRivKEY9J9rHBQqQeTvaGoYbD670RWRaANxaTAzSeDy8Eon" \
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
  azure-cognitive-search \
  --key "$AZURE_SEARCH_API_KEY" \
  --endpoint "$AZURE_SEARCH_ENDPOINT" \
  --index "$DESTINATION_INDEX"

echo "sleeping 5 seconds to let index finish catching up after writes"
sleep 5

# Check the contents of the index
docs=$(curl "https://utic-test-ingest-fixtures.search.windows.net/indexes/$DESTINATION_INDEX/docs/\$count?api-version=$API_VERSION" \
  --header "api-key: $AZURE_SEARCH_API_KEY" \
  --header 'content-type: application/json' | jq)

expected_docs=0
for i in $(jq length "$OUTPUT_DIR"/*); do
  expected_docs=$((expected_docs+i));
done


if [ "$docs" -ne "$expected_docs" ];then
  echo "Number of docs $docs doesn't match the expected docs: $expected_docs"
  exit 1
fi
