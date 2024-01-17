#!/usr/bin/env bash

# Structured outputs are stored in mongodb-ingest-output

PYTHONPATH=. ./unstructured/ingest/main.py \
  mongodb \
  --uri "<MongoDB hosted uri" \
  --database "<MongoDB database>" \
  --collection "<MongoDB collection>" \
  --host "<Host where mongodb database is served>" \
  --port "<Port where mongodb database is served>" \
  --collection "<Collection name to ingest data from>" \
  --batch-size "<How many records to read at a time per process>" \
  --num-processes "<Number of processes to be used to download, ie. 2>"
