#!/usr/bin/env bash

# Processes example-docs/book-war-and-peace-1p.txt/,
# embeds the processed document and writes to results to a Chroma collection.

# Structured outputs are stored in local-to-chroma/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local source connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-chroma \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  chroma \
  --path "<Location where Chroma is persisted, if not connecting via http>" \
  --settings "<Dictionary of settings to communicate with the chroma server>" \
  --tenant "<Tenant to use for this client. Chroma defaults to 'default_tenant'>" \
  --database "<Database to use for this client. Chroma defaults to 'default_database'>" \
  --host "<Hostname of the Chroma server>" \
  --port "<Port of the Chroma server>" \
  --ssl "<Whether to use SSL to connect to the Chroma server>" \
  --headers "<Dictionary of headers to send to the Chroma server>" \
  --collection-name "<Name of the Chroma collection to write into>" \
  --batch-size "<Number of elements to be uploaded in a single batch, ie. 80>"
