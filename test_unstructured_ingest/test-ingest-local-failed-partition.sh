#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-failed-partition
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --num-processes "$max_processes" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --strategy fast \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --input-path "$SCRIPT_DIR"/failed-partition-docs \
    --work-dir "$WORK_DIR"

files=$(find "$OUTPUT_DIR" -type f)
echo "files: $files"
num_files=$(echo  "$files" | wc -l)
if [ "$num_files" -ne 1 ]; then
  echo "There should be only one file that got processed, found: $num_files"
  exit 1
fi
filename=$(basename "$files")
expected_file="small.txt.json"
if [ "$filename" != "$expected_file" ]; then
  echo "The only partitioned file that should exist is $expected_file, instead found $filename"
  exit 1
fi
