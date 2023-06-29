#!/usr/bin/env bash

set -e

if [ -z "$UNS_API_KEY" ]; then
   echo "Skipping ingest test against api because the UNS_API_KEY env var is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --api-key "$UNS_API_KEY" \
    --local-input-path example-docs \
    --local-file-glob "*.pdf" \
    --structured-output-dir api-ingest-output \
    --partition-by-api \
    --partition-strategy hi_res \
    --verbose \
    --reprocess

set +e

if [ "$(find 'api-ingest-output' -type f -printf '.' | wc -c)" != 8 ]; then
   echo
   echo "8 files should have been created."
   exit 1
fi
