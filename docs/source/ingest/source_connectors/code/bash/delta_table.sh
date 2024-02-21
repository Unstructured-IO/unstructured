#!/usr/bin/env bash

unstructured-ingest \
  delta-table \
  --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
  --output-dir delta-table-example \
  --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
  --verbose
