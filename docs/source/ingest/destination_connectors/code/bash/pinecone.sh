#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-pinecone \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  pinecone \
  --api-key "$PINECONE_API_KEY" \
  --index-name "$PINECONE_INDEX_NAME" \
  --environment "$PINECONE_ENVIRONMENT" \
  --batch-size 80
