#!/usr/bin/env bash

# Processes a delta table stored via s3

# Structured outputs are stored in delta-table-output/

# AWS credentials need to be available for use with the storage options
if [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "aws credentials not found as env vars"
  exit 0
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  delta-table \
  --table-uri s3://utic-dev-tech-fixtures/sample-delta-lake-data/deltatable/ \
  --output-dir delta-table-output \
  --num-processes 2 \
  --storage_options "AWS_REGION=us-east-2,AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
  --verbose \
  delta-table \
  --write-column json_data \
  --table-uri delta-table-dest
