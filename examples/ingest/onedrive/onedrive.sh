#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in onedrive-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a Azure AD app client-id, client secret and user principal name  
# before running. 

# To get the credentials for your Azure AD app, follow these steps:
# https://learn.microsoft.com/en-us/graph/auth-register-app-v2
# https://learn.microsoft.com/en-us/graph/auth-v2-service

# Assign the neccesary permissions for the application to read from OneDrive.
# https://learn.microsoft.com/en-us/graph/permissions-reference
 

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --ms-client-id "8ade2b29-1934-4fec-9b4a-f71215fae56d" \
    --ms-client-cred "bAD8Q~xrZfV0UZOtmi61rCIEZA4RYVWxkrHlecAz" \
    --ms-tenant "22175133-950a-4ca9-9fa9-c8d240fb8edc" \
    --ms-user-pname "test-ingest-admin@030rx.onmicrosoft.com" \
    --download-dir onedrive-ingest-input \
    --structured-output-dir onedrive-ingest-output \
    --num-processes 2 \
    --verbose
