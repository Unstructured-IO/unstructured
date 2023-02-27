#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --wikipedia-page-title "Open Source Software" \
    --structured-output-dir wikipedia-ingest-output \
    --num-processes 2 \
    --verbose

if [ "$(find 'wikipedia-ingest-output' -type f -printf '.' | wc -c)" != 3 ]; then
   echo
   echo "3 files should have been created."
   exit 1
fi
