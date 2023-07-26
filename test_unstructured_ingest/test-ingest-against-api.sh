#!/usr/bin/env bash

set -e

if [ -z "$UNS_API_KEY" ]; then
   echo "Skipping ingest test against api because the UNS_API_KEY env var is not set."
   exit 0
fi
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=api-ingest-output
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --api-key "$UNS_API_KEY" \
    --partition-by-api \
    --input-path example-docs

sh "$SCRIPT_DIR"/check-num-files-output.sh 8 $OUTPUT_FOLDER_NAME
