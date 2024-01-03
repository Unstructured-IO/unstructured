#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-opensearch \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 4 \
  --verbose \
  opensearch \
  --hosts "$OPENSEARCH_HOSTS" \
  --username "$OPENSEARCH_USERNAME" \
  --password "$OPENSEARCH_PASSWORD" \
  --index-name "$OPENSEARCH_INDEX_NAME" \
  --num-processes 2
