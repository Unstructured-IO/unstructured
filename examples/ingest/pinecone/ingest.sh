#!/usr/bin/env bash

# Processes all the files from abfs://container1/ in azureunstructured1 account,
# using the `unstructured` library.

# Structured outputs are stored in azure-ingest-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        s3 \
         --remote-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
         --anonymous \
         --output-dir s3-small-batch-output-to-pinecone \
         --num-processes 2 \
         --verbose \
        --strategy fast \
        pinecone \
        --api-key "$PINECONE_API_KEY" \
        --index-name ingest-test \
        --environment "gcp-starter"
