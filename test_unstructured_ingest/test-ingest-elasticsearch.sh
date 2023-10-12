#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
echo "SCRIPT_DIR: $SCRIPT_DIR"
OUTPUT_FOLDER_NAME=elasticsearch
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  # Kill the container so the script can be repeatedly run using the same ports
  echo "Stopping Elasticsearch Docker container"
  docker-compose -f scripts/elasticsearch-test-helpers/docker-compose.yaml down --remove-orphans -v

  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

# shellcheck source=/dev/null
scripts/elasticsearch-test-helpers/create-and-check-es.sh
wait

PYTHONPATH=. ./unstructured/ingest/main.py \
    elasticsearch \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth  \
    --num-processes "$max_processes" \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --index-name movies \
    --url http://localhost:9200 \
    --jq-query '{ethnicity, director, plot}' \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
