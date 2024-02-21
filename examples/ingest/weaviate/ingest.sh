#!/usr/bin/env bash

# Uploads the structured output of the files within the given S3 path to a Weaviate index.

# Structured outputs are stored in s3-small-batch-output-to-weaviate/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes 2 \
  --output-dir weaviate-output \
  --strategy fast \
  --verbose \
  --reprocess \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --work-dir weaviate-work-dir \
  --chunk-elements \
  --chunk-new-after-n-chars 2500 --chunk-multipage-sections \
  --embedding-provider "langchain-huggingface" \
  weaviate \
  --host-url http://localhost:8080 \
  --class-name elements \
  --batch-size 100
