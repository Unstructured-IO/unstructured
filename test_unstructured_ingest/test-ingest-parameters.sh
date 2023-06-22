#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --local-input-path example-docs/english-and-korean.png \
    --structured-output-dir parameterized-ingest-output \
    --partition-strategy hi_res \
    --ocr-languages eng+kor \
    --verbose \
    --reprocess

set +e

if [ "$(grep -c 안녕하세요 parameterized-ingest-output/example-docs/english-and-korean.png.json)" != 1 ]; then
   echo
   echo "--ocr-languages parameter did not work. Did not partition with the specified language pack."
   exit 1
fi
