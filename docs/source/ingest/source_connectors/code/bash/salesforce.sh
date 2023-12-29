#!/usr/bin/env bash

unstructured-ingest \
  salesforce \
  --username "$SALESFORCE_USERNAME" \
  --consumer-key "$SALESFORCE_CONSUMER_KEY" \
  --private-key "$SALESFORCE_PRIVATE_KEY_PATH" \
  --categories "EmailMessage,Account,Lead,Case,Campaign" \
  --output-dir salesforce-output \
  --num-processes 2 \
  --recursive \
  --verbose
