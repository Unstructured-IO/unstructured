#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=github
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$OUTPUT_ROOT/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

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

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
#shellcheck disable=SC2086
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  github \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --strategy hi_res \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --url dcneiner/Downloadify \
  --git-file-glob '*.html,*.txt' \
  --work-dir "$WORK_DIR" \
  $ACCESS_TOKEN_FLAGS

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
