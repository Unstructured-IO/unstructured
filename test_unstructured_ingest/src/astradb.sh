#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=astradb
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
if [ -z "$ASTRA_DB_APPLICATION_TOKEN" ]; then
  echo "Skipping Astra DB source test because ASTRA_DB_APPLICATION_TOKEN env var is not set."
  exit 0
fi

if [ -z "$ASTRA_DB_API_ENDPOINT" ]; then
  echo "Skipping Astra DB source test because ASTRA_DB_API_ENDPOINT env var is not set."
  exit 0
fi

COLLECTION_NAME="ingest_test_src"

PYTHONPATH=. ./unstructured/ingest/main.py \
  astradb \
  --token "$ASTRA_DB_APPLICATION_TOKEN" \
  --api-endpoint "$ASTRA_DB_API_ENDPOINT" \
  --collection-name "$COLLECTION_NAME" \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --strategy hi_res \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
