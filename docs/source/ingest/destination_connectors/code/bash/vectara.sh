#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-vectara \
  --strategy fast \
  --chunk-elements \
  --num-processes 2 \
  --verbose \
  vectara \
  --customer-id "$VECTARA_CUSTOMER_ID" \
  --oauth-client-id "$VECTARA_OAUTH_CLIENT_ID" \
  --oauth-secret "$VECTARA_OAUTH_SECRET" \
  --corpus-name "test-corpus-vectara"
