***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes 3 PDF's from s3://utic-dev-tech-fixtures/small-pdf-set/
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in s3-small-batch-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
         --s3-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
         --s3-anonymous \
         --structured-output-dir s3-small-batch-output \
         --num-processes 2
