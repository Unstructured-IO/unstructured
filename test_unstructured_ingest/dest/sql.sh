#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=sql-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  echo "Stopping SQL DB Docker container"
  docker-compose -f scripts/sql-test-helpers/docker-compose.yml down --remove-orphans -v


  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

# Create sql instance and create `elements` class
echo "Creating SQL DB instance"
# shellcheck source=/dev/null
scripts/sql-test-helpers/create-sql-instance.sh
wait

PYTHONPATH=. ./unstructured/ingest/main.py \
  s3 \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth,metadata.links \
  --strategy fast \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
  --anonymous \
  --work-dir "$WORK_DIR" \
  sql \
    --db_name postgres \
    --username postgres \
    --password test \
    --host http://localhost:8080 \
    --port 5432 \
    --database pdf_elements

scripts/sql-test-helpers/test-ingest-sql-output.py