#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=couchbase-source
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# Check if all necessary environment variables are set
if [ -z "$CB_USERNAME" ] || [ -z "$CB_PASSWORD" ] || [ -z "$CB_CONN_STR" ] || [ -z "$CB_BUCKET" ] || [ -z "$CB_SCOPE" ] || [ -z "$CB_COLLECTION" ]; then
  echo "Error: One or more environment variables are not set. Please set CB_CONN_STR, CB_USERNAME, CB_PASSWORD, CB_BUCKET, CB_SCOPE, and CB_COLLECTION."
  exit 1
fi

#pip uninstall -y couchbase
#make install-ingest-couchbase

PYTHONPATH=. ./unstructured/ingest/main.py \
  couchbase \
  --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.date_created,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --connection-string "$CB_CONN_STR" \
  --bucket "$CB_BUCKET" \
  --username "$CB_USERNAME" \
  --password "$CB_PASSWORD" \
  --scope "$CB_SCOPE" \
  --collection "$CB_COLLECTION" \
  --work-dir "$WORK_DIR" \
  --preserve-downloads \
  --reprocess \
  --batch-size 2 \
  --verbose

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME