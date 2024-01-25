#!/usr/bin/env bash

# Uploads the structured output of the files within the given S3 path.

# Structured outputs are stored in a PostgreSQL instance/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-to-pinecone \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  sql \
  --db-type postgresql \
  --username postgres \
  --password test \
  --host localhost \
  --port 5432 \
  --database elements
