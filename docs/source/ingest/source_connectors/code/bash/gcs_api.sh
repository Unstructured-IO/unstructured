#!/usr/bin/env bash

unstructured-ingest \
  gcs \
  --remote-url gs://utic-test-ingest-fixtures-public/ \
  --output-dir gcs-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
