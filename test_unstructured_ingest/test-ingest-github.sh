#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=github
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

GH_READ_ONLY_ACCESS_TOKEN=${GH_READ_ONLY_ACCESS_TOKEN:-none}

ACCESS_TOKEN_FLAGS=""
# to update test fixtures, "export OVERWRITE_FIXTURES=true" and rerun this script
if [[ "$GH_READ_ONLY_ACCESS_TOKEN" != "none" ]]; then
    ACCESS_TOKEN_FLAGS="--git-access-token $GH_READ_ONLY_ACCESS_TOKEN"
elif [[ "$CI" == "true" ]]; then
    echo "Warning: GH_READ_ONLY_ACCESS_TOKEN is not defined in the CI environment."
    echo "This can lead to intermittent failures in test-ingest-github.sh, as non-auth'ed"
    echo "requests are severely rate limited by GitHub."
    echo
fi

#shellcheck disable=SC2086
PYTHONPATH=. ./unstructured/ingest/main.py \
    github \
    --download-dir "$DOWNLOAD_DIR" \
    --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR" \
    --verbose \
    --url dcneiner/Downloadify \
    --git-file-glob '*.html,*.txt' \
    $ACCESS_TOKEN_FLAGS

sh "$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
