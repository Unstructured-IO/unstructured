#!/usr/bin/env bash

unstructured-ingest \
  azure \
  --remote-url abfs://container1/ \
  --account-name azureunstructured1 \
  --output-dir azure-ingest-output \
  --num-processes 2 \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
