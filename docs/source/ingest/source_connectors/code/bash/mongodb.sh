#!/usr/bin/env bash

unstructured-ingest \
  mongodb \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE" \
  --collection "$MONGODB_COLLECTION" \
  --output-dir mongodb-ingest-output \
  --num-processes 2
