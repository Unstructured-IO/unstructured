#!/usr/bin/env bash
# shellcheck disable=SC2317

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=biomed-path
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

sh "$SCRIPT_DIR"/check-num-files-expected-output.sh 1 $OUTPUT_FOLDER_NAME 10k

PYTHONPATH=. ./unstructured/ingest/main.py \
    --biomed-decay .3 \
    --biomed-max-request-time 30 \
    --biomed-max-retries 5 \
    --biomed-path "oa_pdf/07/07/sbaa031.073.PMC7234218.pdf" \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
