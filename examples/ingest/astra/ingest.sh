#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in astra-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a token, endpoint and collection name
# before running.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  astra \
  --token "<AstraDB Application Token>" \
  --api-endpoint "<AstraDB Api Endpoint>" \
  --collection-name "<AstraDB Collection Name>" \
  --num-processes "2" \
  --output-dir astra-ingest-output \
  --verbose
