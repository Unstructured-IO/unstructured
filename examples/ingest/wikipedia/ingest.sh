***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the Unstructured-IO/unstructured repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in wikipedia-ingest-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --wikipedia-page-title "Open Source Software" \
    --structured-output-dir wikipedia-ingest-output \
    --num-processes 2 \
    --verbose

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --wikipedia-page-title "..." ...
