#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=local-single-file-with-pdf-infer-table-structure
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --partition-by-api \
    --structured-output-dir "$OUTPUT_DIR" \
    --partition-pdf-infer-table-structure True \
    -partition-strategy hi_res \
    --verbose \
    --reprocess \
    --input-path example-docs/layout-parser-paper.pdf

set +e

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
