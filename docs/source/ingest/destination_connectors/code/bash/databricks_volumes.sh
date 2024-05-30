#!/usr/bin/env bash

unstructured-ingest \
  local \
  --input-path example-docs/book-war-and-peace-1p.txt \
  --output-dir local-to-databricks-volume \
  --strategy fast \
  --chunk-elements \
  --embedding-provider "<unstructured embedding provider, ie. langchain-huggingface>" \
  --num-processes 2 \
  --verbose \
  --work-dir "<directory for intermediate outputs to be saved>" \
  databricks-volumes \
  --host "$DATABRICKS_HOST" \
  --username "$DATABRICKS_USERNAME" \
  --password "$DATABRICKS_PASSWORD" \
  --volume "$DATABRICKS_VOLUME" \
  --catalog "$DATABRICKS_CATALOG"
