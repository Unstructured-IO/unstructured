#!/usr/bin/env bash

# Processes 3 PDF's from s3://utic-dev-tech-fixtures/small-pdf-set/
# through Unstructured's library in 2 processes.

# Structured outputs are stored in s3-small-batch-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        s3 \
         --remote-url s3://utic-dev-tech-fixtures/small-pdf-set-w-compression/ \
         --anonymous \
         --output-dir small-pdf-set-w-compression-output \
         --download-dir small-pdf-set-w-compression-download \
         --num-processes 2 \
         --recursive \
         --uncompress \
         --reprocess \
         --verbose
