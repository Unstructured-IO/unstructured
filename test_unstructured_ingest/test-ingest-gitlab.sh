#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=gitlab
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

PYTHONPATH=. ./unstructured/ingest/main.py \
    gitlab \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --git-branch 'v0.0.7' \
    --git-file-glob '*.md,*.txt' \
    --url https://gitlab.com/gitlab-com/content-sites/docsy-gitlab

sh "$SCRIPT_DIR"/check-num-files-output.sh 2 $OUTPUT_FOLDER_NAME
