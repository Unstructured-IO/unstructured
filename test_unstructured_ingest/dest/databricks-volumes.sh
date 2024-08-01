#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=databricks-volumes
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_PATH=$SCRIPT_DIR/databricks-volumes
CI=${CI:-"false"}

RANDOM_SUFFIX=$((RANDOM % 100000 + 1))

DATABRICKS_VOLUME="test-platform"
DATABRICKS_VOLUME_PATH="databricks-volumes-test-output-$RANDOM_SUFFIX"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh

function cleanup() {
  python "$SCRIPT_DIR"/python/test-databricks-volumes.py cleanup \
    --host "$DATABRICKS_HOST" \
    --username "$DATABRICKS_USERNAME" \
    --password "$DATABRICKS_PASSWORD" \
    --volume "$DATABRICKS_VOLUME" \
    --catalog "$DATABRICKS_CATALOG" \
    --volume-path "$DATABRICKS_VOLUME_PATH"

  cleanup_dir "$DESTINATION_PATH"
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --input-path example-docs/pdf/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  databricks-volumes \
  --host "$DATABRICKS_HOST" \
  --username "$DATABRICKS_USERNAME" \
  --password "$DATABRICKS_PASSWORD" \
  --volume "$DATABRICKS_VOLUME" \
  --catalog "$DATABRICKS_CATALOG" \
  --volume-path "$DATABRICKS_VOLUME_PATH"

python "$SCRIPT_DIR"/python/test-databricks-volumes.py test \
  --host "$DATABRICKS_HOST" \
  --username "$DATABRICKS_USERNAME" \
  --password "$DATABRICKS_PASSWORD" \
  --volume "$DATABRICKS_VOLUME" \
  --catalog "$DATABRICKS_CATALOG" \
  --volume-path "$DATABRICKS_VOLUME_PATH"
