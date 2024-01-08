#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/fake-memo.pdf \
  --anonymous \
  --output-dir local-output-to-mongo \
  --num-processes 2 \
  --verbose \
  --strategy fast \
  sql \
  --db-type postgresql \
  --username postgres \
  --password test \
  --host localhost \
  --port 5432 \
  --database elements
