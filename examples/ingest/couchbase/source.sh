#!/usr/bin/env bash

# Structured outputs are stored in couchbase-ingest-output

PYTHONPATH=. ./unstructured/ingest/main.py \
  couchbase \
  --num-processes "<Number of processes to be used to upload, ie. 2>" \
  --connection-string "Couchbase cluster connection string" \
  --username "couchbase cluster username" \
  --password "couchbase cluster password" \
  --bucket "couchbase bucket" \
  --scope "couchbase scope" \
  --collection "couchbase collection" \
  --work-dir "<directory for intermediate outputs to be saved>" \
  --batch-size "<batch size for downloading data from couchbase>"