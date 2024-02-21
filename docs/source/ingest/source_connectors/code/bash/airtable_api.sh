#!/usr/bin/env bash

unstructured-ingest \
  airtable \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
  --output-dir airtable-ingest-output \
  --num-processes 2 \
  --reprocess \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
