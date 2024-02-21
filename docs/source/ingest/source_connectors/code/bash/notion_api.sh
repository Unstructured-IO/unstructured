#!/usr/bin/env bash

unstructured-ingest \
  notion \
  --api-key "<Notion api key>" \
  --output-dir notion-ingest-output \
  --page-ids "<Comma delimited list of page ids to process>" \
  --database-ids "<Comma delimited list of database ids to process>" \
  --num-processes 2 \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
