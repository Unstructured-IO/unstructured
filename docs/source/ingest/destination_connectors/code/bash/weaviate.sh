#!/usr/bin/env bash

unstructured-ingest \
    local \
    --input-path example-docs/fake-memo.pdf \
    --anonymous \
    --output-dir local-output-to-weaviate \
    --num-processes 2 \
    --verbose \
    --strategy fast \
    weaviate \
    --host-url http://localhost:8080 \
    --class-name elements \