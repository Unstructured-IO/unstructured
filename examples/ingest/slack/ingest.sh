#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in slack-ingest-output/

# oldest, latest arguments are optional

# Ingests a slack text channel into a file.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
         --slack-channel 12345678 \
         --slack-token 12345678 \
         --structured-output-dir slack-ingest-output