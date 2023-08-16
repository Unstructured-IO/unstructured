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
    onedrive \
    --client-id "1be61e22-4213-4fc1-9e95-75c93866e2a3" \
    --client-cred "UgK8Q~V.u7gyQxM4RAEaDY2xdBOy3nTiexR6gaXW" \
    --tenant "3d60a7e5-1e32-414e-839b-1c6e6782613d" \
    --user-pname "devops@unstructuredio.onmicrosoft.com" \
    --structured-output-dir onedrive-ingest-output \
    --num-processes 2 \
    --verbose
