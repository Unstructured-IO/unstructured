#!/usr/bin/env bash

# Processes all the files from abfs://container1/ in azureunstructured1 account,
# using the `unstructured` library.

# Structured outputs are stored in azure-ingest-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  azure \
  --remote-url abfs://container1/ \
  --account-name azureunstructured1 \
  --output-dir azure-ingest-output \
  --num-processes 2
