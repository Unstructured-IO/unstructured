#!/usr/bin/env bash

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-mongodb \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  mongodb \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$DESTINATION_MONGO_COLLECTION"
