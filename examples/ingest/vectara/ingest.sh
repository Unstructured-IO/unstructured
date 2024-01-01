#!/usr/bin/env bash

# Processes example-docs/book-war-and-peace-1p.txt/,
# Ingests into Vectara

# Structured outputs are stored in s3-small-batch-output-to-vectara/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the s3 source connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-vectara \
  --strategy fast \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  vectara \
  --api-key "<Vectara API Key to write into a Pinecone index>" \
  --customer-id "<Vectara customer id, ie: ingest-test>" \
  --corpus-id "<Vectara corpus id, ie: ingest-test>"
