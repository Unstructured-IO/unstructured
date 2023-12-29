#!/usr/bin/env bash

# Processes all the files from s3://utic-dev-tech-fixtures/small-pdf-set/,
# embeds the processed documents, and writes to results to a Pinecone index.

# Structured outputs are stored in s3-small-batch-output-to-pinecone/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the s3 source connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
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
  pinecone \
  --api-key "<Pinecone API Key to write into a Pinecone index>" \
  --index-name "<Pinecone index name, ie: ingest-test>" \
  --environment "<Pinecone index name, ie: ingest-test>" \
  --batch-size "<Number of elements to be uploaded per batch, ie. 80>" \
  --num-processes "<Number of processes to be used to upload, ie. 2>"
