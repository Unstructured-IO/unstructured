#!/usr/bin/env bash

unstructured-ingest \
  confluence \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url https://unstructured-ingest-test.atlassian.net \
  --user-email 12345678@unstructured.io \
  --api-token ABCDE1234ABDE1234ABCDE1234 \
  --output-dir confluence-ingest-output \
  --num-processes 2 \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
