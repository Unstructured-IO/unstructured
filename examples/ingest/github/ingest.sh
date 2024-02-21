#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in github-ingest-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  github \
  --url Unstructured-IO/unstructured \
  --git-branch main \
  --output-dir github-ingest-output \
  --num-processes 2 \
  --verbose

# Alternatively, you can call it using:
# unstructured-ingest github --url ...
