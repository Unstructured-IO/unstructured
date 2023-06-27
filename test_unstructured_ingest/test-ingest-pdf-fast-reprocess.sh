#!/usr/bin/env bash
# A local connector to process pre-downloaded PDFs under `files-ingest-download` dir with --fast startegy

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=pdf-fast-reprocess
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    --local-file-glob "*.pdf" \
    --local-input-path "$DOWNLOAD_DIR" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --num-processes 2 \
    --partition-strategy fast \
    --recursive \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
