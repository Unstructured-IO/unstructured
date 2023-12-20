#!/usr/bin/env bash

set -e

DEST_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$DEST_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-dest
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_S3="s3://utic-dev-tech-fixtures/utic-ingest-test-fixtures-output/$(uuidgen)/"
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"

  if aws s3 ls "$DESTINATION_S3" --region us-east-2; then
    echo "deleting destination s3 location: $DESTINATION_S3"
    aws s3 rm "$DESTINATION_S3" --recursive --region us-east-2
  fi

}
trap cleanup EXIT

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/fake-memo.pdf \
  --work-dir "$WORK_DIR" \
  s3 \
  --anonymous \
  --remote-url "$DESTINATION_S3"

# Simply check the number of files uploaded
expected_num_files=1
num_files_in_s3=$(aws s3 ls "${DESTINATION_S3}" --region us-east-2 | grep -c "\.json$")
if [ "$num_files_in_s3" -ne "$expected_num_files" ]; then
  echo "Expected $expected_num_files files to be uploaded to s3, but found $num_files_in_s3 files."
  exit 1
else
  echo "Expected number of files found: $num_files_in_s3/$expected_num_files"
fi
