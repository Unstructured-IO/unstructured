#!/usr/bin/env bash

unstructured-ingest \
  discord \
  --channels 12345678 \
  --token "$DISCORD_TOKEN" \
  --download-dir discord-ingest-download \
  --output-dir discord-example \
  --preserve-downloads \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
