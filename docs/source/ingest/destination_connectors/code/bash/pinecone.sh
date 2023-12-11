#!/usr/bin/env bash

unstructured-ingest \
    local \
    --input-path example-docs/book-war-and-peace-1225p.txt \
    --output-dir local-to-pinecone \
    --strategy fast \
    --chunk-elements \
    --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
    --num-processes 2 \
    --verbose \
    --work-dir "<directory for intermediate outputs to be saved>" \
    pinecone \
    --api-key <your pinecone api key here> \
    --index-name <your index name here, ie. ingest-test> \
    --environment <your environment name here, ie. gcp-starter> \
    --batch-size <number of elements to be uploaded per batch, ie. 80> \
    --num-processes <number of processes to be used to upload, ie. 2>