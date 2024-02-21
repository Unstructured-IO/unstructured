#!/usr/bin/env bash

# Processes Outlook emails through Unstructured's library. Does not download attachments.

# Structured outputs are stored in outlook-output/

# NOTE, this script is not ready-to-run!
# You must enter a Azure AD app client-id, client secret, tenant-id, and email
# before running.

# To get the credentials for your Azure AD app, follow these steps:
# https://learn.microsoft.com/en-us/graph/auth-register-app-v2
# https://learn.microsoft.com/en-us/graph/auth-v2-service

# Assign the neccesary permissions for the application to read from mail.
# https://learn.microsoft.com/en-us/graph/permissions-reference

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  outlook \
  --client-id "$MS_CLIENT_ID" \
  --client-cred "$MS_CLIENT_CRED" \
  --tenant "$MS_TENANT_ID" \
  --user-email "$MS_USER_EMAIL" \
  --outlook-folders "Inbox,Sent Items" \
  --output-dir outlook-output \
  --num-processes 2 \
  --recursive \
  --verbose
