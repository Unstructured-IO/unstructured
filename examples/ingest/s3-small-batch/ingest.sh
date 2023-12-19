#!/usr/bin/env bash

# Processes 3 PDF's from s3://utic-dev-tech-fixtures/small-pdf-set/
# through Unstructured's library in 2 processes.

# Structured outputs are stored in s3-small-batch-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  s3 \
  --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
  --anonymous \
  --output-dir s3-small-batch-output \
  --num-processes 2 \
  --verbose \
  s3 \
  --anonymous \
  --remote-url s3://utic-dev-tech-fixtures/small-pdf-set-output
