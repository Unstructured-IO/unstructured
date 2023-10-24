#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=hubspot
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

if [ -z "$HUBSPOT_API_TOKEN" ]; then
   echo "Skipping HubSpot ingest test because the HUBSPOT_API_TOKEN env var is not set."
   exit 0
fi

# Required arguments:
# --api-token
#   --> HubSpot client API token. Either from a private app or a valid OAuth2 token
#       Check https://developers.hubspot.com/docs/api/private-apps

# Optional arguments:
# --object HubSpot object (i.e ticket) to process. 
#   Can be used multiple times to specify multiple objects.

PYTHONPATH=. ./unstructured/ingest/main.py \
    hubspot \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes "$max_processes" \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --api-token "$HUBSPOT_API_TOKEN" \
    --object-types "calls,communications,emails,notes,products,tickets" \
    --custom-properties "products:my_custom_property,tickets:another_custom_property" \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
