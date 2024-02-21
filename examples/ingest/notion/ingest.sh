#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in notion-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a Notion api key

# To get the credentials for your Notion workspace, follow these steps:
# https://developers.notion.com/docs/create-a-notion-integration

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  notion \
  --api-key "<Notion api key>" \
  --output-dir notion-ingest-output \
  --page-ids "<Comma delimited list of page ids to process>" \
  --database-ids "<Comma delimited list of database ids to process>" \
  --num-processes 2 \
  --verbose
