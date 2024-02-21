#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in slack-ingest-output/

# oldest, latest arguments are optional

# Ingests a slack text channel into a file.
# channels is a comma separated list of channel IDs.
# Bot user must be in the channels for them to be ingested.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  slack \
  --channels 12345678 \
  --token 12345678 \
  --download-dir slack-ingest-download \
  --output-dir slack-ingest-output \
  --start-date 2023-04-01T01:00:00-08:00 \
  --end-date 2023-04-02
