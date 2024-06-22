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
# trap cleanup EXIT

TEST_FILE_NAME=layout-parser-paper-with-table.pdf

# including pdf-infer-table-structure to validate partition arguments are passed to the api
RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  local \
  --api-key "$UNS_API_KEY" \
  --metadata-exclude coordinates,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
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

## .rst is bad
# org, docx, rtf, pptx, odt, xlsx, epub are not supported
  # didn't work
  # --file-glob "README.org,docx-tables.docx,fake-doc.rtf,fake-power-point.pptx,simple.odt,stanley-cups.xlsx,winter-sports.epub" \

  # successful
  # --file-glob "DA-1p.heic,README.md,all-number-table.pdf,book-war-and-peace-1p.txt,copy-protected.pdf,duplicate-paragraphs.doc,example-10k-1p.html,example.jpg,factbook.xml,fake-email.msg,fake-power-point.ppt,layout-parser-paper-fast.tiff,multi-column.pdf,spring-weather.html.jeson,stanley-cups.csv,stanley-cups.tsv,table-multi-row-column-cells.png,tests-example.xls" \

# RESULT_FILE_PATH="$OUTPUT_DIR/$TEST_FILE_NAME.json"
# # validate that there is at least one table with text_as_html in the results
# if [ "$(jq 'any(.[]; .metadata.text_as_html != null)' "$RESULT_FILE_PATH")" = "false" ]; then
#   echo "No table with text_as_html found in $RESULT_FILE_PATH but at least one was expected."
#   exit 1
# fi
