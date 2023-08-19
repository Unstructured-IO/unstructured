#!/usr/bin/env bash

# Processes several files in a nested folder structure from dropbox://utic-test-ingest-fixtures/
# through Unstructured's library in 2 processes.
# Due to Dropbox's interesting sdk:
# if you want files and folders from the root directory use `"dropbox:// /"`
# if your files and folders are in a subfolder it is normal like `dropbox://nested-1`

# To get or refresh an access token use dropbox_token.py

# Structured outputs are stored in dropbox-output/

# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1


PYTHONPATH=. ./unstructured/ingest/main.py \
  salesforce \
   --salesforce-username "$SALESFORCE_USERNAME" \
   --salesforce-consumer-key "$SALESFORCE_CONSUMER_KEY" \
   --salesforce-private-key_path "$SALESFORCE_PRIVATE_KEY_PATH" \
   --salesforce-categories "EmailMessage,Account,Lead" \
   --structured-output-dir salesforce-output \
   --download-dir salesforce-download \
   --preserve-downloads \
   --reprocess \
   --verbose