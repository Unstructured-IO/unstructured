#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --local-input-path example-docs \
    --local-file-glob "*.html" \
    --structured-output-dir local-ingest-output \
    --verbose

if [ "$(find 'local-ingest-output' -type f -printf '.' | wc -c)" != 4 ]; then
   echo
   echo "4 files should have been created."
   exit 1
fi
