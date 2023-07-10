#!/usr/bin/env bash

# Processes all the documents in all spaces within a confluence domain, using the `unstructured` library.

# Structured outputs are stored in confluence-ingest-output
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/../../.. || exit 1

# Obtain your authentication variables,
# and name them as $CONFLUENCE_USER_EMAIL and $CONFLUENCE_API_TOKEN.

# you can save them in another file and source from there for security reasons:
# source "./../../secrets/confluence2.txt"

PYTHONPATH=. ./unstructured/ingest/main.py \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --confluence-url https://unstructured-ingest-test.atlassian.net \
        --confluence-user-email 12345678@unstructured.io \  #replace with: "$CONFLUENCE_USER_EMAIL"
        --confluence-api-token ABCDE1234ABDE1234ABCDE1234 \  #replace with: "$CONFLUENCE_API_TOKEN"
        --structured-output-dir confluence-ingest-output \
        --num-processes 2
