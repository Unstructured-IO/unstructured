#!/usr/bin/env bash

unstructured-ingest \
  github \
  --url Unstructured-IO/unstructured \
  --git-branch main \
  --output-dir github-ingest-output \
  --num-processes 2 \
  --verbose
