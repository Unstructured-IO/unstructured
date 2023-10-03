#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in sharepoint-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a MS Sharepoint app client-id, client secret and sharepoint site url
# before running.

# To get the credentials for your Sharepoint app, follow these steps:
# https://github.com/vgrem/Office365-REST-Python-Client/wiki/How-to-connect-to-SharePoint-Online-and-and-SharePoint-2013-2016-2019-on-premises--with-app-principal



SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    sharepoint \
    --client-id $SHAREPOINT_CLIENT_ID \
    --client-cred $SHAREPOINT_CRED \
    --application-id-rbac $SHAREPOINT_RBAC_CLIENT_APPLICATION_ID \
    --client-cred-rbac $SHAREPOINT_RBAC_CLIENT_SECRET \
    --site $SHAREPOINT_SITE \
    --rbac-tenant $SHAREPOINT_RBAC_TENANT \
    --output-dir sharepoint-ingest-output \
    --num-processes 2 \
    --path "Shared Documents" \
    --verbose
# --files-only "Flag to process only files within the site(s)" \
