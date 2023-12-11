#!/usr/bin/env bash

unstructured-ingest \
    local \
    --input-path example-docs/book-war-and-peace-1225p.txt \
    --output-dir local-output-to-pinecone \
    --strategy fast \
    --chunk-elements \
    --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
    --num-processes 2 \
    --verbose \
    --work-dir "<directory for intermediate outputs to be saved>" \
    pinecone \
    --api-key "$PINECONE_API_KEY" \
    --index-name "$PINECONE_INDEX_NAME" \
    --environment "$PINECONE_ENVIRONMENT" \
    --batch-size 80