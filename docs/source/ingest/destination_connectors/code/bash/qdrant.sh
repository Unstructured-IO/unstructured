#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-qdrant \
  --strategy fast \
  --chunk-strategy by_title \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  qdrant \
  --collection-name "$QDRANT_COLLECTION_NAME" \
  --location "http://localhost:6333" \
  --batch-size 80
