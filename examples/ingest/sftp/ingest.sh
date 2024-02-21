#!/usr/bin/env bash

# Processes several files in a nested folder structure from sftp://address:port/upload/
# through Unstructured's library in 2 processes.

# Structured outputs are stored in sftp-output/

# Uses fsspec and paramiko to connect to the sftp server

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  sftp \
  --remote-url sftp://address:port/upload \
  --username foo \
  --password bar \
  --output-dir sftp-output \
  --num-processes 2 \
  --recursive \
  --verbose
