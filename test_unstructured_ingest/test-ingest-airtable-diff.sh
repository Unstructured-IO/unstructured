#!/usr/bin/env bash
set -e

# Description: This test checks if all the processed content is the same as the expected outputs.
# Also checks if a large table can be ingested properly.

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=airtable-diff
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

VARIED_DATA_BASE_ID="app5YQxSfp220fWtm"
VARIED_DATA_BASE_ID_2="appJ43QmP8I17zu88"

if [ -z "$AIRTABLE_PERSONAL_ACCESS_TOKEN" ]; then
   echo "Skipping Airtable ingest test because the AIRTABLE_PERSONAL_ACCESS_TOKEN is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    airtable \
    --download-dir "$DOWNLOAD_DIR" \
    --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
    --list-of-paths "$VARIED_DATA_BASE_ID $VARIED_DATA_BASE_ID_2" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.date,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes "$max_processes" \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
