#!/usr/bin/env bash

# Processes multiple files in a nested folder structure from Salesforce
# through Unstructured's library in 2 processes.

# Available categories are: EmailMessage, Account, Lead, Case, Campaign

# Structured outputs are stored in salesforce-output/

# Using JWT authorization
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm

# salesforce-private-key-path is the path to the key file

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1


PYTHONPATH=. ./unstructured/ingest/main.py \
  salesforce \
   --salesforce-username "$SALESFORCE_USERNAME" \
   --salesforce-consumer-key "$SALESFORCE_CONSUMER_KEY" \
   --salesforce-private-key-path "$SALESFORCE_PRIVATE_KEY_PATH" \
   --salesforce-categories "EmailMessage,Account,Lead,Case,Campaign" \
   --structured-output-dir salesforce-output \
   --download-dir salesforce-download \
   --preserve-downloads \
   --reprocess \
   --verbose