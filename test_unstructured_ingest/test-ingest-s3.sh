#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=s3
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
DESTINATION_S3="s3://utic-dev-tech-fixtures/small-pdf-set-output/$(date +%s)/"
OUTPUT_FOLDER_NAME_DEST=s3_dest
OUTPUT_DIR_DEST=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME_DEST

sh "$SCRIPT_DIR"/check-num-files-expected-output.sh 3 $OUTPUT_FOLDER_NAME 20k

function cleanup() {
  echo "--- Running cleanup ---"

  if [ -d "$OUTPUT_DIR" ]; then
    echo "cleaning up tmp directory: $OUTPUT_DIR"
    rm -rf "$OUTPUT_DIR"
  fi

  if aws s3 ls "$DESTINATION_S3"; then
    echo "deleting destination s3 location: $DESTINATION_S3"
    aws s3 rm "$DESTINATION_S3" --recursive --region us-east-2
  fi

  if [ -d "$OUTPUT_DIR_DEST" ]; then
    echo "cleaning up tmp directory: $OUTPUT_DIR_DEST"
    rm -rf "$OUTPUT_DIR_DEST"
  fi
  echo "--- Cleanup done ---"

}

trap cleanup EXIT

PYTHONPATH=. ./unstructured/ingest/main.py \
    s3 \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
    --anonymous \
    s3 \
    --anonymous \
    --remote-url "$DESTINATION_S3"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME

# Check against content uploaded to s3

aws s3 cp "$DESTINATION_S3" "$OUTPUT_DIR_DEST" --recursive --no-sign-request --region us-east-2

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME_DEST
