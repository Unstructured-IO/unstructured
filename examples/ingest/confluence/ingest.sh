#!/usr/bin/env bash

# Processes all the documents in all spaces within a confluence domain, using the `unstructured` library.

# Structured outputs are stored in confluence-ingest-output
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/../../.. || exit 1

# Obtain your authentication variables, save/source them from another file, for security reasons:
# source "./../../secrets/confluence.txt"
# ...
# --confluence-user-email "$CONFLUENCE_USER_EMAIL"
# --confluence-api-token "$CONFLUENCE_API_TOKEN"

# Other arguments that you can use:
# --confluence-max-num-of-spaces 10
#     --> The maximum number of spaces to be ingested. Set as 10 in the example.
# --confluence-list-of-spaces testteamsp1,testteamsp2
#     --> A comma separated list of space ids for the spaces to be ingested.
#     --> Avoid using --confluence-list-of-spaces and --confluence-max-num-of-spaces at the same time.
# --confluence-max-num-of-docs-from-each-space 250 \
#     --> The maximum number of documents to be ingested from each space. Set as 250 in the example.
PYTHONPATH=. ./unstructured/ingest/main.py \
        --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
        --confluence-url https://unstructured-ingest-test.atlassian.net \
        --confluence-user-email 12345678@unstructured.io \
        --confluence-api-token ABCDE1234ABDE1234ABCDE1234 \
        --structured-output-dir confluence-ingest-output \
        --num-processes 2
