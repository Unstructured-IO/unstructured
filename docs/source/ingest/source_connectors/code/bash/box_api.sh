#!/usr/bin/env bash

unstructured-ingest \
  box \
  --box_app_config "$BOX_APP_CONFIG_PATH" \
  --remote-url box://utic-test-ingest-fixtures \
  --output-dir box-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
