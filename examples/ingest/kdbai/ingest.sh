#!/usr/bin/env bash

# Processes example-docs/book-war-and-peace-1p.txt/,
# embeds the processed document and writes to results to a KDB.AI table.

# Structured outputs are stored in local-to-kdbai/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local source connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-kdbai \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "langchain-huggingface" \
  --num-processes 2 \
  --verbose \
  chroma \
  --api-key "<Private KDB.AI key to connect with the instance>" \
  --endpoint "<KDB.AI endpoint>" \
  --table-name "<KDB.AI table name, ie: elements>" \
  --batch-size "<Number of elements to be uploaded per batch, ie. 100>" 

