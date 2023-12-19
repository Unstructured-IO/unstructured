#!/usr/bin/env bash

unstructured-ingest \
  google-drive \
  --drive-id "<file or folder id>" \
  --service-account-key "<path to drive service account key>" \
  --output-dir google-drive-ingest-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
