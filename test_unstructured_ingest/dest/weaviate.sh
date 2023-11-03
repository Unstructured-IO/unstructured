#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=weaviate-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup {
  # Index cleanup
  echo "Stopping Weaviate Docker container"
  docker-compose -f scripts/weaviate-test-helpers/docker-compose.yml down --remove-orphans -v


  # Local file cleanup
  cleanup_dir "$WORK_DIR"
  cleanup_dir "$OUTPUT_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

# Create weaviate instance and create `elements` class
echo "Creating weaviate instance"
# shellcheck source=/dev/null
scripts/weaviate-test-helpers/create-weaviate-instance.sh
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
  weaviate \
  --host-url http://localhost:8080 \
  --class-name pdf_elements \

scripts/weaviate-test-helpers/test-ingest-weaviate-output.py