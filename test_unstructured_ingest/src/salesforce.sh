#!/usr/bin/env bash

# Set either SALESFORCE_PRIVATE_KEY (app config json content as string) or
# SALESFORCE_PRIVATE_KEY_PATH (path to app config json file) env var

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=salesforce
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

if [ -z "$SALESFORCE_USERNAME" ] || [ -z "$SALESFORCE_CONSUMER_KEY" ]; then
  echo "Skipping Salesforce ingest test because SALESFORCE_USERNAME and SALESFORCE_CONSUMER_KEY env vars not set"
  exit 8
fi

if [ -z "$SALESFORCE_PRIVATE_KEY" ] && [ -z "$SALESFORCE_PRIVATE_KEY_PATH" ]; then
  echo "Skipping Salesforce ingest test because neither SALESFORCE_PRIVATE_KEY nor SALESFORCE_PRIVATE_KEY_PATH env vars are set."
  exit 8
fi

if [ -z "$SALESFORCE_PRIVATE_KEY_PATH" ]; then
  # Create temporary service key file
  SALESFORCE_PRIVATE_KEY_PATH=$(mktemp)
  echo "$SALESFORCE_PRIVATE_KEY" >"$SALESFORCE_PRIVATE_KEY_PATH"
fi

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  salesforce \
  --categories "EmailMessage,Campaign" \
  --download-dir "$DOWNLOAD_DIR" \
  --username "$SALESFORCE_USERNAME" \
  --consumer-key "$SALESFORCE_CONSUMER_KEY" \
  --private-key "$SALESFORCE_PRIVATE_KEY_PATH" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --preserve-downloads \
  --recursive \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
