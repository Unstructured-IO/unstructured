#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in reddit-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a client ID and a client secret before running.
# You can find out how to get them here:
# https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps
# It is quite easy and very quick.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --subreddit-name machinelearning \
    --reddit-client-id "<client id here>" \
    --reddit-client-secret "<client secret here>" \
    --reddit-user-agent "Unstructured Ingest Subreddit fetcher by \u\..." \
    --reddit-search-query "Unstructured" \
    --reddit-num-posts 10 \
    --structured-output-dir reddit-ingest-output \
    --num-processes 2 \
    --verbose

# Alternatively, you can call it using:
# unstructured-ingest --subreddit-name ...
