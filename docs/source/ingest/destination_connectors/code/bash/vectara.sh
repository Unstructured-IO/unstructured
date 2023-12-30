#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-vectara \
  --strategy fast \
  --chunk-elements \
  --num-processes 2 \
  --verbose \
  pinecone \
  --api-key "$VECTARA_API_KEY" \
  --customer-id "$VECTARA_CUSTOMER_ID" \
  --corpus-id "$VECTARA_CORPUS_ID" \
  --batch-size 10
