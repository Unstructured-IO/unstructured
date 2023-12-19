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

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  onedrive \
  --client-id "<Azure AD app client-id>" \
  --client-cred "<Azure AD app client-secret>" \
  --authority-url "<Authority URL, default is https://login.microsoftonline.com>" \
  --tenant "<Azure AD tenant_id, default is 'common'>" \
  --user-pname "<Azure AD principal name, in most cases is the email linked to the drive>" \
  --path "<Path to start parsing files from>" \
  --output-dir onedrive-ingest-output \
  --num-processes 2 \
  --verbose
