#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=discord
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$DISCORD_TOKEN" ]; then
   echo "Skipping Discord ingest test because the DISCORD_TOKEN env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
   --discord-channels 1099442333440802930,1099601456321003600 \
   --discord-token "$DISCORD_TOKEN" \
   --download-dir "$DOWNLOAD_DIR" \
   --metadata-exclude coordinates,file_directory,metadata.data_source.date_processed \
   --preserve-downloads \
   --reprocess \
    --structured-output-dir "$OUTPUT_DIR"

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
