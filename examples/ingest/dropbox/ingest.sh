#!/usr/bin/env bash

# Processes several files in a nested folder structure from gs://unstructured_public/ 
# through Unstructured's library in 2 processes.

# Structured outputs are stored in dropbox-output/


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

# 
   # --remote-url "dropbox:// /" \
#    --remote-url "dropbox://nested-1" \

PYTHONPATH=. ./unstructured/ingest/main.py \
   --remote-url "dropbox:// /" \
   --structured-output-dir dropbox-output \
   --dropbox-token  $DROPBOX_TOKEN \
   --num-processes 2 \
   --recursive \
   --verbose 