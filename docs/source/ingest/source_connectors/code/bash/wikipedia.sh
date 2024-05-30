#!/usr/bin/env bash

unstructured-ingest \
  wikipedia \
  --page-title "Open Source Software" \
  --output-dir wikipedia-ingest-output \
  --num-processes 2 \
  --verbose
