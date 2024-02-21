#!/usr/bin/env bash

unstructured-ingest \
  dropbox \
  --remote-url "dropbox:// /" \
  --output-dir dropbox-output \
  --token "$DROPBOX_TOKEN" \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
