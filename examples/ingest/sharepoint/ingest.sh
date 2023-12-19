#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in sharepoint-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a MS Sharepoint app client-id, client secret and sharepoint site url
# before running.

# To get the credentials for your Sharepoint app, follow these steps:
# https://github.com/vgrem/Office365-REST-Python-Client/wiki/How-to-connect-to-SharePoint-Online-and-and-SharePoint-2013-2016-2019-on-premises--with-app-principal

# To optionally set up your application and obtain permissions related variables (--permissions-application-id, --permissions-client-cred, --permissions-tenant), follow these steps:
# https://tsmatz.wordpress.com/2016/10/07/application-permission-with-v2-endpoint-and-microsoft-graph

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  sharepoint \
  --client-id "<Microsoft Sharepoint app client-id>" \
  --client-cred "<Microsoft Sharepoint app client-secret>" \
  --site "<e.g https://contoso.sharepoint.com or https://contoso.admin.sharepoint.com to process all sites within tenant>" \
  --permissions-application-id "<Microsoft Graph API application id to process per-file access permissions>" \
  --permissions-client-cred "<Microsoft Graph API application credentials to process per-file access permissions>" \
  --permissions-tenant "<e.g https://contoso.onmicrosoft.com to process per-file access permissions>" \
  --files-only "Flag to process only files within the site(s)" \
  --output-dir sharepoint-ingest-output \
  --num-processes 2 \
  --path "Shared Documents" \
  --verbose
