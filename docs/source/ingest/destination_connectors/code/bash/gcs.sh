#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-gcs \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  gcs \
  --service-account-key "$SERVICE_ACCOUNT_KEY" \
  --remote-url "<your destination path here, ie 'gcs://unstructured/war-and-peace-output'>"
