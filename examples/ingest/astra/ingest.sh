#!/usr/bin/env bash

# Processes all the files from abfs://container1/ in AZURE_ACCOUNT_NAME account,
# using the `unstructured` library.

# Structured outputs are stored in azure-ingest-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  azure \
  --remote-url abfs://container1/ \
  --account-name "<AZURE_ACCOUNT_NAME>" \
  --output-dir azure-ingest-output \
  --num-processes 2

ASTRAAAAA
