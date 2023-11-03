#!/usr/bin/env bash

# Uploads the structured output of the files within the given S3 path.

# Structured outputs are stored in azure-ingest-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        s3 \
         --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
         --anonymous \
         --output-dir s3-small-batch-output-to-sql \
         --num-processes 2 \
         --verbose \
        --strategy fast \
        sql \
        --db_name postgres \
        --username postgres \
        --password test \
        --host http://localhost:8080 \
        --port 5432 \
        --database pdf_elements
