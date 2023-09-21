#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=dropbox
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

if [ -z "$DROPBOX_APP_KEY" ] || [ -z "$DROPBOX_APP_SECRET" ] || [ -z "$DROPBOX_REFRESH_TOKEN" ]; then
   echo "Skipping Dropbox ingest test because one or more of these env vars is not set:"
   echo "DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN"
   exit 0
fi

# Get a new access token from Dropbox
DROPBOX_RESPONSE=$(curl https://api.dropbox.com/oauth2/token -d refresh_token="$DROPBOX_REFRESH_TOKEN" -d grant_type=refresh_token -d client_id="$DROPBOX_APP_KEY" -d client_secret="$DROPBOX_APP_SECRET")
DROPBOX_ACCESS_TOKEN=$(jq -r '.access_token' <<< "$DROPBOX_RESPONSE")

PYTHONPATH=. ./unstructured/ingest/main.py \
    dropbox \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --token  "$DROPBOX_ACCESS_TOKEN" \
    --recursive \
    --remote-url "dropbox:// /"


"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
