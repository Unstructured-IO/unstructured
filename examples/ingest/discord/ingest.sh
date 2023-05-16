#!/usr/bin/env bash

# Ingests a discord text channel into a file.

# Structured outputs are stored in discord-example/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        --discord-channels 12345678 \
        --discord-token "$DISCORD_TOKEN" \
        --download-dir discord-ingest-download \
        --structured-output-dir discord-example
