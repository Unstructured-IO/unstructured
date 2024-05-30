#!/usr/bin/env bash

unstructured-ingest \
  jira \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url https://unstructured-jira-connector-test.atlassian.net \
  --user-email 12345678@unstructured.io \
  --api-token ABCDE1234ABDE1234ABCDE1234 \
  --output-dir jira-ingest-output \
  --num-processes 2
