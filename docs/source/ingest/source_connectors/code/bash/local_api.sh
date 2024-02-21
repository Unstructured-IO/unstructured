#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs \
  --output-dir local-ingest-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
