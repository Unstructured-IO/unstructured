#!/usr/bin/env bash

unstructured-ingest \
  s3 \
  --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
  --anonymous \
  --output-dir s3-small-batch-output \
  --num-processes 2
