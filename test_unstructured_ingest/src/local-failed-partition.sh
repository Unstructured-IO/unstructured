#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-failed-partition
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  echo "RUNNING CLEANUP"
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}

trap cleanup EXIT

function check() {
  # Currently, unstructured doesn't support .gif files for partitioning so only one of the files should
  # get successfully partitioned. If support for .gif files is ever added, that test file
  # should be updated to another non-supported filetype
  files=$(find "$OUTPUT_DIR" -type f)
  echo "files: $files"

  "$SCRIPT_DIR"/check-num-files-output.sh 1 "$OUTPUT_FOLDER_NAME"

  filename=$(basename "$files")
  expected_file="small.txt.json"
  if [ "$filename" != "$expected_file" ]; then
    echo "The only partitioned file that should exist is $expected_file, instead found $filename"
    exit 1
  fi
}

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --strategy fast \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --input-path "$SCRIPT_DIR"/failed-partition-docs \
  --work-dir "$WORK_DIR"

check
