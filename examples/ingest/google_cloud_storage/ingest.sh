#!/usr/bin/env bash

# Processes several files in a nested folder structure from gs://utic-test-ingest-fixtures-public/
# through Unstructured's library in 2 processes.

# Structured outputs are stored in gcs-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  gcs \
  --remote-url gs://utic-test-ingest-fixtures-public/ \
  --output-dir gcs-output \
  --num-processes 2 \
  --recursive \
  --verbose
