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
  --oauth-client-id "<Vectara OAUTH2 client ID" \
  --oauth-secret "<Vectara OAUTH2 Secret" \
  --customer-id "<Vectara customer id" \
  --corpus-name "<Vectara corpus name>"
