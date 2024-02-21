#!/usr/bin/env bash

unstructured-ingest \
  reddit \
  --subreddit-name machinelearning \
  --client-id "<client id here>" \
  --client-secret "<client secret here>" \
  --user-agent "Unstructured Ingest Subreddit fetcher by \u\..." \
  --search-query "Unstructured" \
  --num-posts 10 \
  --output-dir reddit-ingest-output \
  --num-processes 2 \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
