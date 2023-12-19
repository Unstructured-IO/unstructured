#!/usr/bin/env bash

unstructured-ingest \
  sftp \
  --remote-url sftp://address:port/upload \
  --username foo \
  --password bar \
  --output-dir sftp-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
