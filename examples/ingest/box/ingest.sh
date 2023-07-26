#!/usr/bin/env bash

# Processes several files in a nested folder structure from box://utic-test-ingest-fixtures/ 
# through Unstructured's library in 2 processes.

# Structured outputs are stored in box-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
   --remote-url box://utic-test-ingest-fixtures/ \
   --structured-output-dir box-output \
   --box-jwt "$BOX_JWT" \
   --num-processes 2 \
   --recursive \
   --verbose 