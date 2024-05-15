#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-kdbai \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  kdbai \
  --endpoint "KDB.AI endpoint" \
  --api-key "private api-key" \
  --table-name "table name" \
  --batch-size 80
