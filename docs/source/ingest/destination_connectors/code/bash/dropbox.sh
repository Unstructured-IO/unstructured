#!/usr/bin/env bash

unstructured-ingest \
    local \
    --input-path example-docs/book-war-and-peace-1225p.txt \
    --output-dir local-output-to-dropbox \
    --strategy fast \
    --chunk-elements \
    --embedding-provider <an unstructured embedding provider, ie. langchain-huggingface> \
    --num-processes 2 \
    --verbose \
    --work-dir "<directory for intermediate outputs to be saved>" \
    dropbox \
    --token  "$DROPBOX_TOKEN" \
    --remote-url "<your destination path here, ie 'dropbox://unstructured/war-and-peace-output'>"