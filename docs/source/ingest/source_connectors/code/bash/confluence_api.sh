#!/usr/bin/env bash

unstructured-ingest \
  confluence \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url https://unstructured-ingest-test.atlassian.net \
  --user-email "$CONFLUENCE_USER_EMAIL" \
  --api-token "$CONFLUENCE_API_TOKEN" \
  --output-dir confluence-ingest-output \
  --num-processes 2 \
  --partition-by-api \
  --api-key "$UNSTRUCTURED_API_KEY"
