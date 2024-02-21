#!/usr/bin/env bash

unstructured-ingest \
  slack \
  --channels 12345678 \
  --token 12345678 \
  --download-dir slack-ingest-download \
  --output-dir slack-ingest-output \
  --start-date 2023-04-01T01:00:00-08:00 \
  --end-date 2023-04-02
