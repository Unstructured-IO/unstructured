#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in local-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter:
#   1) --local-input-path  : path in the local file system which is to be processed
#   2) --local-file-glob   : types of local files that are accepted,
#                            provided as a comma-separated list
# before running.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --local-input-path example-docs \
    --local-file-glob "<comma-separated list of file globs>" \
    --structured-output-dir local-ingest-output \
    --num-processes 2 \
    --local-recursive \
    --verbose \
#   Example: `--local-file-glob .docx` ensures only .docx files are processed.
#   NOTE: `--local-recursive` is optional

# Alternatively, you can call it using:
# unstructured-ingest --local-input-path ...
