#!/usr/bin/env bash

# Processes a the file from local, chunks, embeds, and writes the results to an opensearch index.

# Structured outputs are stored in local-to-opensearch/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-to-opensearch \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  opensearch \
  --hosts "<List of URLs where opensearch index is served>" \
  --index-name "<Index name to upload data in>" \
  --username "<Username to authenticate into the index>" \
  --password "<Password to authenticate into the index>" \
  --batch-size-bytes "<Size limit for any batch to be uploaded, in bytes, ie. 15000000>" \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --ca-certs "<path/to/ca/certs>" \
  --client-cert "<path/to/client/cert>" \
  --client-key "<path/to/client/key>" \
  --use-ssl \
  --verify-certs \
  --ssl-show-warn
