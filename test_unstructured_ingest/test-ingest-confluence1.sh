#!/usr/bin/env bash
set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

# Tests the scenario where there is no --confluence-list-of-spaces provided, with
# a low number of documents in the spaces.
OUTPUT_FOLDER_NAME=confluence1
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$CONFLUENCE_USER_EMAIL" ] || [ -z "$CONFLUENCE_API_TOKEN" ]; then
   echo "Skipping Confluence ingest test because the CONFLUENCE_USER_EMAIL or CONFLUENCE_API_TOKEN env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --download-dir "$DOWNLOAD_DIR" \
    --confluence-url https://unstructured-ingest-test.atlassian.net \
    --confluence-user-email "$CONFLUENCE_USER_EMAIL" \
    --confluence-api-token "$CONFLUENCE_API_TOKEN" \
    --confluence-num-of-spaces 4 \
    --confluence-num-of-docs-from-each-space 4 \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
