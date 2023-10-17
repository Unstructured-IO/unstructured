#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=azure-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

if [ -z "$AZURE_DEST_CONNECTION_STR" ]; then
   echo "Skipping Azure destination ingest test because the AZURE_DEST_CONNECTION_STR env var is not set."
   exit 0
fi

CONTAINER=utic-ingest-test-fixtures-output
DIRECTORY=$(date +%s)
REMOTE_URL="abfs://$CONTAINER/$DIRECTORY/"

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  echo "deleting azure storage blob directory $CONTAINER/$DIRECTORY"
  az storage fs directory delete -f "$CONTAINER" -n "$DIRECTORY" --connection-string "$AZURE_DEST_CONNECTION_STR" --yes

}
trap cleanup EXIT

# Create directory to use for testing
az storage fs directory create -f "$CONTAINER" --n "$DIRECTORY" --connection-string "$AZURE_DEST_CONNECTION_STR"

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
    azure \
    --overwrite \
    --remote-url "$REMOTE_URL" \
    --connection-string "$AZURE_DEST_CONNECTION_STR"

# Simply check the number of files uploaded
expected_num_files=1
num_files_in_azure=$(az storage blob list -c "$CONTAINER" --prefix "$DIRECTORY"/example-docs/ --connection-string "$AZURE_DEST_CONNECTION_STR" | jq 'length')
if [ "$num_files_in_azure" -ne "$expected_num_files" ]; then
    echo "Expected $expected_num_files files to be uploaded to azure, but found $num_files_in_azure files."
    exit 1
fi
