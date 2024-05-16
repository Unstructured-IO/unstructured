#!/usr/bin/env bash

unstructured-ingest \
  sftp \
  --remote-url sftp://address:port/upload \
  --username "$SFTP_USERNAME" \
  --password "$SFTP_PASSWORD" \
  --output-dir sftp-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "$UNSTRUCTURED_API_KEY"
