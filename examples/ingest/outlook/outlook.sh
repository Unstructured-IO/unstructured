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
# user-pname is the email address of the Outlook mailbox
 
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --ms-client-id "$MS_CLIENT_ID" \
    --ms-client-cred "$MS_CLIENT_CRED" \
    --ms-authority-url "https://login.microsoftonline.com" \
    --ms-tenant "$MS_TENANT" \
    --ms-user-pname "$MS_USER_PNAME" \
    --ms-outlook-folder "Inbox" \
    --structured-output-dir outlook-ingest-output \
    --num-processes 2 \
    --download-dir outlook-download \
    --recursive \
    --verbose
