#!/usr/bin/env bash

# Processes several files in a nested folder structure from dropbox://utic-test-ingest-fixtures/
# through Unstructured's library in 2 processes.
# Due to Dropbox's interesting sdk:
# if you want files and folders from the root directory use `"dropbox:// /"`
# if your files and folders are in a subfolder it is normal like `dropbox://nested-1`

# To get or refresh an access token use dropbox_token.py

# Structured outputs are stored in dropbox-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  dropbox \
  --remote-url "dropbox:// /" \
  --output-dir dropbox-output \
  --token "$DROPBOX_TOKEN" \
  --num-processes 2 \
  --recursive \
  --verbose
