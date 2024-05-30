#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-chroma \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  chroma \
  --host "localhost" \
  --port 8000 \
  --collection-name "collection name" \
  --tenant "default_tenant" \
  --database "default_database" \
  --batch-size 80
