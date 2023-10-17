#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3-dest
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$SCRIPT_DIR/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
DESTINATION_S3="s3://utic-dev-tech-fixtures/utic-ingest-test-fixtures-output/$(date +%s)/"

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
    s3 \
    --anonymous \
    --remote-url "$DESTINATION_S3"

# Simply check the number of files uploaded
expected_num_files=1
num_files_in_s3=$(aws s3 ls "$DESTINATION_S3/example-docs/" --region us-east-2 | wc -l)
if [ "$num_files_in_s3" -ne "$expected_num_files" ]; then
    echo "Expected $expected_num_files files to be uploaded to s3, but found $num_files_in_s3 files."
    exit 1
fi
