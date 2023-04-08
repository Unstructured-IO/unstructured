***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the Unstructured-IO/unstructured repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in slack-ingest-output/

***REMOVED*** oldest, latest arguments are optional

***REMOVED*** Ingests a slack text channel into a file.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
         --slack-channel 12345678 \
         --slack-token 12345678 \
         --download-dir slack-ingest-download \
         --structured-output-dir slack-ingest-output \
         --oldest 2023-04-01T01:00:00-08:00 \
         --latest 2023-04-02
