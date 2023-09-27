#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_INDEX="utic-test-ingest-fixtures-output-demo"
# The vector configs on the schema currently only exist on versions:
# 2023-07-01-Preview, 2021-04-30-Preview, 2020-06-30-Preview
API_VERSION=2023-07-01-Preview


function run_env_var_checks(){
  # Run all env var checks
  if [ -z "$SHAREPOINT_CLIENT_ID" ] || [ -z "$SHAREPOINT_CRED" ] ; then
     echo "SHAREPOINT_CLIENT_ID and SHAREPOINT_CRED env var are required."
     exit 1
  fi

  if [ -z "$OPENAI_API_KEY" ]; then
     echo "OPENAI_API_KEY env var is required."
     exit 1
  fi

  if [ -z "$AZURE_SEARCH_ENDPOINT" ] && [ -z "$AZURE_SEARCH_API_KEY" ]; then
     echo "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY are required."
     exit 1
  fi
}

function cleanup {
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
}


function print_help() {
  echo "help: $0 [up|down]"
}

function create_index() {
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
}

function run_partition() {
  PYTHONPATH=. ./unstructured/ingest/main.py \
    sharepoint \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --client-cred "$SHAREPOINT_CRED" \
    --client-id "$SHAREPOINT_CLIENT_ID" \
    --site "$SHAREPOINT_SITE" \
    --path "Shared Documents" \
    --recursive \
    --embedding-api-key "$OPENAI_API_KEY" \
    --chunk-elements \
    --chunk-multipage-sections \
    azure-cognitive-search \
    --key "$AZURE_SEARCH_API_KEY" \
    --endpoint "$AZURE_SEARCH_ENDPOINT" \
    --index "$DESTINATION_INDEX"
}

if [ "$#" -ne 1 ]; then
    print_help
    exit 1
fi

action=$1

case $action in
  up)
    echo "Spinning things up..."
    run_env_var_checks
    create_index
    run_partition
    ;;
  down)
    echo "running tear down..."
    cleanup
    ;;
  *)
    print_help
    exit 1
    ;;
esac
