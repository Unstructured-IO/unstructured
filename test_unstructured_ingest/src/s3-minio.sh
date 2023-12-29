#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-minio
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
secret_key=minioadmin
access_key=minioadmin

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
# shellcheck disable=SC2317
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

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
AWS_SECRET_ACCESS_KEY=$secret_key AWS_ACCESS_KEY_ID=$access_key \
  PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
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

set +e
"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "The last script run exited with a non-zero exit code: $EXIT_CODE."
  # Handle the error or exit
fi

"$SCRIPT_DIR"/evaluation-ingest-cp.sh "$OUTPUT_DIR" "$OUTPUT_FOLDER_NAME"

exit $EXIT_CODE
