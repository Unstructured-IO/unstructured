#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=dropbox
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

if [ -z "$DROPBOX_APP_KEY" ] || [ -z "$DROPBOX_APP_SECRET" ] || [ -z "$DROPBOX_REFRESH_TOKEN" ]; then
  echo "Skipping Dropbox ingest test because one or more of these env vars is not set:"
  echo "DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN"
  exit 8
fi

# Get a new access token from Dropbox
DROPBOX_RESPONSE=$(curl https://api.dropbox.com/oauth2/token -d refresh_token="$DROPBOX_REFRESH_TOKEN" -d grant_type=refresh_token -d client_id="$DROPBOX_APP_KEY" -d client_secret="$DROPBOX_APP_SECRET")
DROPBOX_ACCESS_TOKEN=$(jq -r '.access_token' <<<"$DROPBOX_RESPONSE")

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  dropbox \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --token "$DROPBOX_ACCESS_TOKEN" \
  --recursive \
  --remote-url "dropbox://test-input/" \
  --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
