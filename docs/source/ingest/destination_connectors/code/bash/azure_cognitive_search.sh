#!/usr/bin/env bash
EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-azure-cog-search \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  azure-cognitive-search \
  --key "$AZURE_SEARCH_API_KEY" \
  --endpoint "$AZURE_SEARCH_ENDPOINT" \
  --index utic-test-ingest-fixtures-output
