#!/usr/bin/env bash
#TODO currently box api/sdk does not work to create folders and check for content similar to other fsspec ingest tests

#
#set -e
#
#DEST_PATH=$(dirname "$(realpath "$0")")
#SCRIPT_DIR=$(dirname "$DEST_PATH")
#cd "$SCRIPT_DIR"/.. || exit 1
#OUTPUT_FOLDER_NAME=box-dest
#OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
#WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
#max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
#DESTINATION_BOX="box://utic-dev-tech-fixtures/utic-ingest-test-fixtures-output/$(date +%s)/"
#
#CI=${CI:-"false"}
#
#if [ -z "$BOX_APP_CONFIG" ] && [ -z "$BOX_APP_CONFIG_PATH" ]; then
#   echo "Skipping Box ingest test because neither BOX_APP_CONFIG nor BOX_APP_CONFIG_PATH env vars are set."
#   exit 0
#fi
#
#if [ -z "$BOX_APP_CONFIG_PATH" ]; then
#    # Create temporary service key file
#    BOX_APP_CONFIG_PATH=$(mktemp)
#    echo "$BOX_APP_CONFIG" >"$BOX_APP_CONFIG_PATH"
#fi
#
## shellcheck disable=SC1091
#source "$SCRIPT_DIR"/cleanup.sh
#function cleanup() {
#  cleanup_dir "$OUTPUT_DIR"
#  cleanup_dir "$WORK_DIR"
#    if [ "$CI" == "true" ]; then
#    cleanup_dir "$DOWNLOAD_DIR"
#  fi
#}
#trap cleanup EXIT
#
#PYTHONPATH=. ./unstructured/ingest/main.py \
#    local \
#    --num-processes "$max_processes" \
#    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
#    --output-dir "$OUTPUT_DIR" \
#    --strategy fast \
#    --verbose \
#    --reprocess \
#    --input-path example-docs/fake-memo.pdf \
#    --work-dir "$WORK_DIR" \
#    box \
#    --box-app-config "$BOX_APP_CONFIG_PATH" \
#    --remote-url "$DESTINATION_BOX" \
#
## Simply check the number of files uploaded
#expected_num_files=1
