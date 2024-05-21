#!/usr/bin/env bash

# Uploads the structured output of the files within the given path to a clarifai app.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-output-to-clarifai \
  --strategy fast \
  --chunk-strategy by_title \
  --num-processes 2 \
  --verbose \
  clarifai \
  --app-id "<your clarifai app name>" \
  --user-id "<your clarifai user id>" \
  --api-key "<your clarifai PAT key>" \
  --batch-size 100
