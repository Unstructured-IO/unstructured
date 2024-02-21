#!/usr/bin/env bash

# Processes files in example-docs/ directory recursively
# through Unstructured's library in 2 processes.

# Structured outputs are stored in local-ingest-output/

# To use the Local connector, the following is required:
#   1) --local-input-path  : path in the local file system which is to be processed
# The following CLI args are optional:
#   2) --local-file-glob   : types of local files that are accepted,
#                            provided as a comma-separated list
#      Example: `--local-file-glob .docx` ensures only .docx files are processed.
#   3) --local-recursive   : if specified, the contents of sub-directories are processed as well

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs \
  --output-dir local-ingest-output \
  --num-processes 2 \
  --recursive \
  --verbose

# Alternatively, you can call it using:
# unstructured-ingest local --input-path ...
