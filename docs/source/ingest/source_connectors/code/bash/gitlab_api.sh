#!/usr/bin/env bash

unstructured-ingest \
  gitlab \
  --url https://gitlab.com/gitlab-com/content-sites/docsy-gitlab \
  --git-branch 'v0.0.7' \
  --output-dir gitlab-ingest-output \
  --num-processes 2 \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
