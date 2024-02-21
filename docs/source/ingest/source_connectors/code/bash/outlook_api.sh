#!/usr/bin/env bash

unstructured-ingest \
  outlook \
  --client-id "$MS_CLIENT_ID" \
  --client-cred "$MS_CLIENT_CRED" \
  --tenant "$MS_TENANT_ID" \
  --user-email "$MS_USER_EMAIL" \
  --outlook-folders Inbox,"Sent Items" \
  --output-dir outlook-output \
  --num-processes 2 \
  --recursive \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
