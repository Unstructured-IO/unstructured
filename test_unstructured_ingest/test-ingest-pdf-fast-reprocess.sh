#!/usr/bin/env bash
# A local connector to process pre-downloaded PDFs under `files-ingest-download` dir with --fast startegy

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=pdf-fast-reprocess
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
INPUT_PATH=$SCRIPT_DIR/download

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

echo "REPROCESS INPUT PATH"
ls "$INPUT_PATH"

PYTHONPATH=. ./unstructured/ingest/main.py \
    local \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
    --num-processes 2 \
    --strategy fast \
    --reprocess \
    --output-dir "$OUTPUT_DIR" \
    --verbose \
    --file-glob "*.pdf" \
    --input-path "$INPUT_PATH" \
    --recursive



"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
