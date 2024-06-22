#!/usr/bin/env bash

# Tests the following filetypes against Open Source:
# .csv, .doc, .docx, .epub, .heic, .html, .jpg, .md, .msg, .odt, .org, .pdf, .png, .ppt, .pptx, .rst, .rtf, .tiff, .tsv, .txt, .xls, .xlsx, .xml
# All should partition fine


set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
OUTPUT_FOLDER_NAME=multi-doc-against-open-source-output
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
}
trap cleanup EXIT

TEST_FILE_NAME=layout-parser-paper-with-table.pdf

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --api-key "$UNS_API_KEY" \
  --metadata-exclude coordinates,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth,metadata.data_source.date_processed \
  --strategy hi_res \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --file-glob "all-number-table.pdf, \
book-war-and-peace-1p.txt, \
copy-protected.pdf, \
DA-1p.heic, \
docx-tables.docx, \
duplicate-paragraphs.doc, \
example-10k-1p.html, \
example.jpg, \
factbook.xml, \
fake-doc.rtf, \
fake-email.msg, \
fake-power-point.ppt, \
fake-power-point.pptx, \
layout-parser-paper-fast.tiff, \
multi-column-2p.pdf, \
README.md, \
README.org, \
simple.odt, \
spring-weather.html.json, \
stanley-cups.csv, \
stanley-cups.tsv, \
stanley-cups.xlsx, \
table-multi-row-column-cells.png, \
tests-example.xls, \
winter-sports.epub" \
  --num-processes "1" \
  --input-path "example-docs/" \
  --work-dir "$WORK_DIR"


"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
