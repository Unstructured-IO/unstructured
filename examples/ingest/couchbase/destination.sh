#!/usr/bin/env bash

# Processes a the file from local, chunks, embeds, and writes the results to a Couchbase Collection.

# Structured outputs are stored in local-to-couchbase/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --output-dir local-to-couchbase \
  --strategy fast \
  --verbose \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --work-dir "<directory for intermediate outputs to be saved>" \
  --chunking-strategy by_title \
  --chunk-max-characters "max characters per document to chunk" \
  --chunk-multipage-sections \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  couchbase \
 --connection-string "Couchbase cluster connection string" \
  --username "couchbase cluster username" \
  --password "couchbase cluster password" \
  --bucket "couchbase bucket" \
  --scope "couchbase scope" \
  --collection "couchbase collection where data will be stored as multiple documents" \
  --batch-size 80