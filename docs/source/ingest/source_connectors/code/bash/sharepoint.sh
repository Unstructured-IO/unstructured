#!/usr/bin/env bash

unstructured-ingest \
  sharepoint \
  --client-id "<Microsoft Sharepoint app client-id>" \
  --client-cred "<Microsoft Sharepoint app client-secret>" \
  --site "<e.g https://contoso.sharepoint.com or https://contoso.admin.sharepoint.com to process all sites within tenant>" \
  --permissions-application-id "<Microsoft Graph API application id, to process per-file access permissions>" \
  --permissions-client-cred "<Microsoft Graph API application credentials, to process per-file access permissions>" \
  --permissions-tenant "<e.g https://contoso.onmicrosoft.com (tenant URL) to process per-file access permissions>" \
  --files-only "Flag to process only files within the site(s)" \
  --output-dir sharepoint-ingest-output \
  --num-processes 2 \
  --path "Shared Documents" \
  --verbose
