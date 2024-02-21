#!/usr/bin/env bash

# Processes multiple files in a nested folder structure from Salesforce
# through Unstructured's library in 2 processes.

# Available categories are: Account, Case, Campaign, EmailMessage, Lead

# Structured outputs are stored in salesforce-output/

# Using JWT authorization
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm
# https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm

# private-key is the path to the key file or key contents

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  salesforce \
  --username "$SALESFORCE_USERNAME" \
  --consumer-key "$SALESFORCE_CONSUMER_KEY" \
  --private-key "$SALESFORCE_PRIVATE_KEY_PATH" \
  --categories "EmailMessage,Account,Lead,Case,Campaign" \
  --output-dir salesforce-output \
  --preserve-downloads \
  --reprocess \
  --verbose
