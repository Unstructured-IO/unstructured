#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-clarifai \
  --strategy fast \
  --chunk-elements \
  --num-processes 2 \
  --verbose \
  clarifai \
  --app-id "$CLARIFAI_APP_ID" \
  --user-id "$CLARIFAI_USER_ID" \
  --api-key "$CLARIFAI_PAT_KEY" \
  --batch-size 100
