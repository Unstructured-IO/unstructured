#!/usr/bin/env bash

# Processes all the files from abfs://container1/ in azureunstructured1 account,
# using the `unstructured` library.

# Structured outputs are stored in azure-ingest-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

# We remove chunking params until the chunk/embed ordering fix is merged
PYTHONPATH=. ./unstructured/ingest/main.py \
        s3 \
         --remote-url "<url to ingest from, ie: s3://utic-dev-tech-fixtures/small-pdf-set/>" \
         --anonymous \
         --output-dir s3-small-batch-output-to-pinecone \
         --num-processes 2 \
         --verbose \
         --strategy fast \
         --embedding-api-key "<api key to use openai embeddings>" \
        pinecone \
        --api-key "<api key to use pinecone>" \
        --index-name "<your index name, ie ingest-test>" \
        --environment <your environment name, ie gcp-starter"
