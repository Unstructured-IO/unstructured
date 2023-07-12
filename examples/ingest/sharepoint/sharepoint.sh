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
    --ms-client-id "dbef1311-451c-425b-aa41-865a11bd67ab" \
    --ms-client-cred "KjCgbv1wT0XzE0j5ync+tQA7UR0hGq8GjRP3qYyl5ag=" \
    --ms-sharepoint-site "https://unstructuredio.sharepoint.com/" \
    --ms-sharepoint-pages \
    --structured-output-dir sharepoint-ingest-output \
    --download-dir sharepoint-ingest-input \
    --num-processes 2 \
    --verbose
