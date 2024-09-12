#!/usr/bin/env bash

# ------------------------------------------------------------------------------------------------
# This test exercises the `--chunk-no-include-orig-elements` option which turns off inclusion of
# `.metadata.orig_elements` in chunks. It also exercises the `--chunk-no-multipage-sections`
# option which otherwise has no other coverage.
# ------------------------------------------------------------------------------------------------

set -e

# -- Test Parameters: These vary by test file, others are common computed values --
TEST_ROOT_NAME=local-single-file-chunk-no-orig-elements
EXAMPLE_DOC=multi-column-2p.pdf

# -- computed parameters, common across similar tests --
SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=$TEST_ROOT_NAME
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
# -- use absolute path of input file to verify passing an absolute path --
ABS_INPUT_PATH="$SCRIPT_DIR/../example-docs/pdf/$EXAMPLE_DOC"
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
# shellcheck disable=SC2317
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}

PYTHONPATH=. unstructured-ingest \
  local \
  --chunking-strategy by_title \
  --chunk-no-include-orig-elements \
  --chunk-max-characters 2000 \
  --chunk-no-multipage-sections \
  --input-path "$ABS_INPUT_PATH" \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_created,metadata.data_source.date_modified,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --output-dir "$OUTPUT_DIR" \
  --reprocess \
  --verbose \
  --work-dir "$WORK_DIR"

set +e
"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ]; then
  echo "The last script run exited with a non-zero exit code: $EXIT_CODE."
  # Handle the error or exit
fi

"$SCRIPT_DIR"/evaluation-ingest-cp.sh "$OUTPUT_DIR" "$OUTPUT_FOLDER_NAME"

exit $EXIT_CODE
