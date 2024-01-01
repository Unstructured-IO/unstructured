#!/usr/bin/env bash

# Uploads the structured output of the files within the given path to a Qdrant collection named 'test'.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-"langchain-huggingface"}

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-qdrant \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "$EMBEDDING_PROVIDER" \
  --num-processes 2 \
  --verbose \
  qdrant \
  --collection-name "test" \
  --location "http://localhost:6333" \
  --batch-size 80
