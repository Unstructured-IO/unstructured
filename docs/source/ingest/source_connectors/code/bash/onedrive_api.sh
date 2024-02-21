#!/usr/bin/env bash

unstructured-ingest \
  onedrive \
  --client-id "<Azure AD app client-id>" \
  --client-cred "<Azure AD app client-secret>" \
  --authority-url "<Authority URL, default is https://login.microsoftonline.com>" \
  --tenant "<Azure AD tenant_id, default is 'common'>" \
  --user-pname "<Azure AD principal name, in most cases is the email linked to the drive>" \
  --path "<Path to start parsing files from>" \
  --output-dir onedrive-ingest-output \
  --num-processes 2 \
  --verbose \
  --partition-by-api \
  --api-key "<UNSTRUCTURED-API-KEY>"
