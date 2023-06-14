#!/usr/bin/env bash

# Processes several files in a nested folder structure from gs://unstructured_public/ 
# through Unstructured's library in 2 processes.

# Structured outputs are stored in gcs-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
   --remote-url gs://unstructured_public/ \
   --structured-output-dir gcs-output \
   --num-processes 2 \
   --recursive \
   --verbose 