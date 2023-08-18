#!/usr/bin/env bash
set -e

# Description: This test checks if the number of spaces and documents processed are as expected.
# Each space shows up as a directory in the output folder, hence check-num-dirs-output.sh
# Each document shows up as a file in a space directory, hence check-num-files-output.sh

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=confluence-large
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$CONFLUENCE_USER_EMAIL" ] || [ -z "$CONFLUENCE_API_TOKEN" ]; then
   echo "Skipping Confluence ingest test because the CONFLUENCE_USER_EMAIL or CONFLUENCE_API_TOKEN env var is not set."
   exit 0
fi

# The test checks the scenario where --confluence-list-of-spaces and --confluence-num-of-spaces
# are being provided at the same time, which is a wrong way to use the connector.

# We expect the test to ignore --confluence-num-of-spaces and use --confluence-list-of-spaces.
PYTHONPATH=. ./unstructured/ingest/main.py \
    confluence \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --num-processes 2 \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --url https://unstructured-ingest-test.atlassian.net \
    --user-email "$CONFLUENCE_USER_EMAIL" \
    --api-token "$CONFLUENCE_API_TOKEN" \
    --max-num-of-spaces 10 \
    --list-of-spaces testteamsp1 \
    --max-num-of-docs-from-each-space 250 \

OUTPUT_SUBFOLDER_NAME=testteamsp1

# We are expecting two directories: one for the space, and one is the output directory itself
# Example:
# Output dir: unstructured/test_unstructured_ingest/structured-output/confluence-large
# Space dir: unstructured/test_unstructured_ingest/structured-output/confluence-large/testteamsp1
sh "$SCRIPT_DIR"/check-num-dirs-output.sh 2 "$OUTPUT_FOLDER_NAME"

# We are expecting 250 files due to the --confluence-num-of-docs-from-each-space 250 that we provided.
sh "$SCRIPT_DIR"/check-num-files-output.sh 250 "$OUTPUT_FOLDER_NAME"/"$OUTPUT_SUBFOLDER_NAME"/
