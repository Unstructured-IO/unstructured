#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=api-ingest-output
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    --local-file-glob "*.pdf" \
    --local-input-path example-docs \
    --partition-by-api \
    --partition-strategy hi_res \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose

sh "$SCRIPT_DIR"/check-num-files-output.sh 8 $OUTPUT_FOLDER_NAME
