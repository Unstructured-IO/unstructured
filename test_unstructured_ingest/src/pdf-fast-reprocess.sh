#!/usr/bin/env bash
# A local connector to process pre-downloaded PDFs under `/download` dir with --fast startegy

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=pdf-fast-reprocess
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
INPUT_PATH=$SCRIPT_DIR/download
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$INPUT_PATH"
  fi
}
trap cleanup EXIT

echo "REPROCESS INPUT PATH"
ls "$INPUT_PATH"

RUN_SCRIPT=${RUN_SCRIPT:-unstructured-ingest}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --metadata-exclude coordinates,filename,file_directory,metadata.data_source.date_created,metadata.data_source.date_modified,metadata.data_source.date_processed,metadata.data_source.filesize_bytes,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --strategy fast \
  --reprocess \
  --verbose \
  --file-glob "*.pdf" \
  --input-path "$INPUT_PATH" \
  --recursive \
  --work-dir "$WORK_DIR" \
  local \
  --output-dir "$OUTPUT_DIR"

# Flatten outputs so paths match fixtures. New behavior for downloads in unstructured-ingest is to create a nested directory structure.
mkdir -p "$OUTPUT_DIR/azure"
find "$OUTPUT_DIR/azure" -type f -name '*.json' -path '*/unstructured_*/*' -print0 | while IFS= read -r -d '' f; do
  mv "$f" "$OUTPUT_DIR/azure/$(basename "$f")"
done
find "$OUTPUT_DIR/azure" -type d -name 'unstructured_*' -exec rm -rf {} +

# Normalize record_locator.path to drop unstructured_* in the download path
python3 - <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
for p in root.rglob('*.json'):
    s = p.read_text()
    s2 = re.sub(r'(/download/azure)/unstructured_[^/]+/', r'\1/', s)
    if s2 != s:
        p.write_text(s2)
PY "$OUTPUT_DIR/azure"


"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
