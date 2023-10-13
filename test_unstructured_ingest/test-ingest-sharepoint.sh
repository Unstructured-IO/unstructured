#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=Sharepoint
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
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

if [ -z "$SHAREPOINT_CLIENT_ID" ] || [ -z "$SHAREPOINT_CRED" ]; then
   echo "Skipping Sharepoint ingest test because the SHAREPOINT_CLIENT_ID or SHAREPOINT_CRED env var is not set."
   exit 0
fi

if [ -z "$SHAREPOINT_PERMISSIONS_APP_ID" ] || [ -z "$SHAREPOINT_PERMISSIONS_APP_CRED" ] || [ -z "$SHAREPOINT_PERMISSIONS_TENANT" ] ; then
   echo "Skipping Sharepoint ingest test because the SHAREPOINT_PERMISSIONS_APP_ID, SHAREPOINT_PERMISSIONS_APP_CRED, or SHAREPOINT_PERMISSIONS_TENANT env var is not set."
   exit 0
fi

# excluding metadata.last_modified since this will always update as date processed because the Sharepoint connector creates documents on the fly
PYTHONPATH=. ./unstructured/ingest/main.py \
    sharepoint \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes "$max_processes" \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --client-cred "$SHAREPOINT_CRED" \
    --client-id "$SHAREPOINT_CLIENT_ID" \
    --site "$SHAREPOINT_SITE" \
    --permissions-application-id "$SHAREPOINT_PERMISSIONS_APP_ID" \
    --permissions-client-cred "$SHAREPOINT_PERMISSIONS_APP_CRED" \
    --permissions-tenant "$SHAREPOINT_PERMISSIONS_TENANT" \
    --path "Shared Documents" \
    --recursive \
    --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
