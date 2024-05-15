#!/usr/bin/env bash

unstructured-ingest \
  azure \
  --remote-url abfs://container1/ \
  --account-name "$AZURE_ACCOUNT_NAME" \
  --output-dir azure-ingest-output \
  --num-processes 2
