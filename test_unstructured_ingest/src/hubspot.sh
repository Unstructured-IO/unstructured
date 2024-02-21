#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=hubspot
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

if [ -z "$HUBSPOT_API_TOKEN" ]; then
  echo "Skipping HubSpot ingest test because the HUBSPOT_API_TOKEN env var is not set."
  exit 8
fi

# Required arguments:
# --api-token
#   --> HubSpot client API token. Either from a private app or a valid OAuth2 token
#       Check https://developers.hubspot.com/docs/api/private-apps

# Optional arguments:
# --object HubSpot object (i.e ticket) to process.
#   Can be used multiple times to specify multiple objects.
# --custom-properties Custom property to process information from. Comma separated list.

PYTHONPATH=. ./unstructured/ingest/main.py \
  hubspot \
  --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.date_created,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --api-token "$HUBSPOT_API_TOKEN" \
  --object-types "calls,communications,emails,notes,products,tickets" \
  --custom-properties '{"products":["my_custom_property"],"tickets":["another_custom_property"]}' \
  --work-dir "$WORK_DIR" \
  --preserve-downloads \
  --verbose

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
