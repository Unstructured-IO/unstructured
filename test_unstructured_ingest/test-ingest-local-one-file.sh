#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

set -e

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --local-input-path example-docs/fake-html.html \
    --structured-output-dir local-ingest-output2 \
    --verbose \
    --reprocess

set +e

if [ "$(find 'local-ingest-output' -type f -printf '.' | wc -c)" != 4 ]; then
   echo
   echo "4 files should have been created."
   exit 1
fi
