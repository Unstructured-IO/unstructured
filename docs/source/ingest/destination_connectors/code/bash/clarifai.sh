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
  --app-id "<your clarifai app name>" \
  --user-id "<your clarifai user id>" \
  --api-key "<your clarifai PAT key>" \
  --batch-size 100
