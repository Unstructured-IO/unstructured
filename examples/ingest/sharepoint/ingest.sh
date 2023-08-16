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
    --client-id "dbef1311-451c-425b-aa41-865a11bd67ab" \
    --client-cred "KjCgbv1wT0XzE0j5ync+tQA7UR0hGq8GjRP3qYyl5ag=" \
    --site "https://unstructuredio.sharepoint.com/" \
    --files-only \
    --structured-output-dir sharepoint-ingest-output \
    --num-processes 2 \
    --verbose
