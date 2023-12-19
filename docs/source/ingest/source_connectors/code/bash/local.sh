#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs \
  --output-dir local-ingest-output \
  --num-processes 2 \
  --recursive \
  --verbose
