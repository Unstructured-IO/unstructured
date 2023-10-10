#!/usr/bin/env bash

set -e


SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-minio
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
secret_key=minioadmin
access_key=minioadmin

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  # Kill the container so the script can be repeatedly run using the same ports
  echo "Stopping Minio Docker container"
  docker-compose -f scripts/minio-test-helpers/docker-compose.yaml down --remove-orphans -v

  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}

trap cleanup EXIT

# shellcheck source=/dev/null
scripts/minio-test-helpers/create-and-check-minio.sh
wait

AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key PYTHONPATH=. ./unstructured/ingest/main.py \
    s3 \
    --num-processes "$max_processes" \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.data_source.date_modified,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --remote-url s3://utic-dev-tech-fixtures/ \
    --endpoint-url http://localhost:9000 \
    --work-dir "$WORK_DIR"


"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
