#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=gcs-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_GCS="gs://utic-test-ingest-fixtures-output/$(date +%s)"
CI=${CI:-"false"}

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
    echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
    exit 0
fi

# Create temporary service key file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
echo "$GCP_INGEST_SERVICE_KEY" > "$GCP_INGEST_SERVICE_KEY_FILE"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi

  if gcloud storage ls "$DESTINATION_GCS"; then
    echo "deleting $DESTINATION_GCS"
    gcloud storage rm --recursive "$DESTINATION_GCS"
  fi

}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --num-processes "$max_processes" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --output-dir "$OUTPUT_DIR" \
    --strategy fast \
    --verbose \
    --reprocess \
    --input-path example-docs/fake-memo.pdf \
    --work-dir "$WORK_DIR" \
    gcs \
    --service-account-key "$GCP_INGEST_SERVICE_KEY_FILE" \
    --remote-url "$DESTINATION_GCS"

# Simply check the number of files uploaded
expected_num_files=1
num_files_in_gcs=$(gcloud storage ls "$DESTINATION_GCS"/example-docs/ | wc -l )
if [ "$num_files_in_gcs" -ne "$expected_num_files" ]; then
    echo "Expected $expected_num_files files to be uploaded to gcs, but found $num_files_in_gcs files."
    exit 1
fi
