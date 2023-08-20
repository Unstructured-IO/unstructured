#!/usr/bin/env bash

# Set either SALESFORCE_PRIVATE_KEY (app config json content as string) or
# SALESFORCE_PRIVATE_KEY_PATH (path to app config json file) env var

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=salesforce
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$SALESFORCE_PRIVATE_KEY" ] && [ -z "$SALESFORCE_PRIVATE_KEY_PATH" ]; then
   echo "Skipping Salesforce ingest test because neither SALESFORCE_PRIVATE_KEY nor SALESFORCE_PRIVATE_KEY_PATH env vars are set."
   exit 0
fi

if [ -z "$SALESFORCE_PRIVATE_KEY_PATH" ]; then
    # Create temporary service key file
    SALESFORCE_PRIVATE_KEY_PATH=$(mktemp)
    echo "$SALESFORCE_PRIVATE_KEY" >"$SALESFORCE_PRIVATE_KEY_PATH"
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    salesforce \
    --salesforce-categories "EmailMessage,Campaign" \
    --download-dir "$DOWNLOAD_DIR" \
    --salesforce-username "$SALESFORCE_USERNAME" \
    --salesforce-consumer-key "$SALESFORCE_CONSUMER_KEY" \
    --salesforce-private-key-path "$SALESFORCE_PRIVATE_KEY_PATH" \
    --salesforce-categories "EmailMessage,Campaign" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --num-processes 2 \
    --preserve-downloads \
    --recursive \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME