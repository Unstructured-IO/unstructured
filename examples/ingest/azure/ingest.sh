#!/usr/bin/env bash

# Processes all the files from abfs://demo-files/ in datalakebenja22 account, 
# using the `unstructured` library.

# Structured outputs are stored in azure-demo-files-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        --remote-url abfs://demo-files/ \
        --azure-account-name datalakebenja22 \
        --structured-output-dir azure-demo-files-output \
        --num-processes 2
