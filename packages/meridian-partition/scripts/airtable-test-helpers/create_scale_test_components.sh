#!/usr/bin/env bash

# This scripts creates a large number of tables inside an Airtable base.

# shellcheck disable=SC2001,SC1091
source ./scripts/airtable-test-helpers/component_ids.sh

base_data='{"description": "Table-X of the test tables for the test LARGE_BASE.", "fields": [{"description": "Name of the row","name": "Name","type": "singleLineText"}],"name": "LARGE_BASE_TABLE_X"}'
for ((i = 1; i <= 100; i++)); do
  item="$(echo "$base_data" | sed "s/X/$i/g")"
  curl -X POST "https://api.airtable.com/v0/meta/bases/$LARGE_BASE_BASE_ID/tables" \
    -H "Authorization: Bearer $AIRTABLE_ACCESS_TOKEN_WRITE2" \
    -H "Content-Type: application/json" \
    --data "$item"
done
