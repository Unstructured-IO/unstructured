#!/usr/bin/env bash

unstructured-ingest \
  reddit \
  --subreddit-name machinelearning \
  --client-id "$REDDIT_CLIENT_ID" \
  --client-secret "$REDDIT_CLIENT_SECRET" \
  --user-agent "Unstructured Ingest Subreddit fetcher by \u\..." \
  --search-query "Unstructured" \
  --num-posts 10 \
  --output-dir reddit-ingest-output \
  --num-processes 2 \
  --verbose \
  --partition-by-api \
  --api-key "$UNSTRUCTURED_API_KEY"
