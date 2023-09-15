#!/usr/bin/env bash
# shellcheck disable=SC2317

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=biomed-path
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup "$OUTPUT_DIR"' EXIT

sh "$SCRIPT_DIR"/check-num-files-expected-output.sh 1 $OUTPUT_FOLDER_NAME 10k

PYTHONPATH=. ./unstructured/ingest/main.py \
    biomed \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.last_modified,metadata.data_source.date_processed,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --decay .3 \
    --max-request-time 30 \
    --max-retries 5 \
    --path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
