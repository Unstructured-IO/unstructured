#!/usr/bin/env bash

# Processes a the file from local, chunks, embeds, and writes the results to an MongoDB collection.

# Structured outputs are stored in local-to-mongodb/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-to-mongodb \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  mongodb \
  --uri "<MongoDB hosted uri" \
  --database "<MongoDB database>" \
  --collection "<MongoDB collection>" \
  --host "<Host where MongoDB database is served>" \
  --port "<Port where MongoDB database is served>" \
  --collection "<Collection name to ingest data from>"
