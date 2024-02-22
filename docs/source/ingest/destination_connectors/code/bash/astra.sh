#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-output-to-pinecone \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  astra \
  --token "$ASTRA_DB_TOKEN" \
  --api-endpoint "$ASTRA_DB_ENDPOINT" \
  --collection-name "$COLLECTION_NAME" \
  --embedding-dimension "$EMBEDDING_DIMENSION"
