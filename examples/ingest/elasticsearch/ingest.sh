#!/usr/bin/env bash

# Processes all the files in http://localhost:9200 in an index named 'movies' using the `unstructured` library.
# This URL is assumed to serve an elasticsearch cluster with an index named 'movies'.

# Structured outputs are stored in elasticsearch-ingest-output

# TODO: provide inputs / outputs, and an elasticsearch server setup script to test automatically
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        --elasticsearch-url http://localhost:9200 \
        --elasticsearch-index-name movies \
        --jq-query '{ethnicity, director}' \
        --structured-output-dir elasticsearch-ingest-output \
        --num-processes 2 \
