#!/usr/bin/env bash

# Processes a the file from local, chunks, embeds, and writes the results to an Elasticsearch index.

# Structured outputs are stored in local-to-elasticsearch/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

# As an example we're using the local connector,
# however ingesting from any supported source connector is possible.
# shellcheck disable=2094
PYTHONPATH=. ./unstructured/ingest/main.py \
  local \
  --input-path example-docs/book-war-and-peace-1225p.txt \
  --output-dir local-to-elasticsearch \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<an unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  elasticsearch \
  --hosts "<List of URLs where elasticsearch index is served>" \
  --index-name "<Index name to upload data in>" \
  --username "<Username to authenticate into the index>" \
  --password "<Password to authenticate into the index>" \
  --batch-size-bytes "<Size limit for any batch to be uploaded, in bytes, ie. 15000000>" \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --cloud-id "<Id used to connect to Elastic Cloud>" \
  --es-api-key "<Api key used for authentication>" \
  --api-key-id "<Id associated with api key used for authentication: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html>" \
  --bearer-auth "<Bearer token used for HTTP bearer authentication>" \
  --ca-certs "<path/to/ca/certs>" \
  --ssl-assert-fingerprint "<SHA256 fingerprint value>"
