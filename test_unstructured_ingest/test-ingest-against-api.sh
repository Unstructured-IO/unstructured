#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --local-input-path example-docs \
    --local-file-glob "*.pdf" \
    --structured-output-dir api-ingest-output \
    --partition-by-api \
    --partition-strategy hi_res \
    --verbose \
    --reprocess

set +e

if [ "$(find 'api-ingest-output' -type f -printf '.' | wc -c)" != 5 ]; then
   echo
   echo "5 files should have been created."
   exit 1
fi
