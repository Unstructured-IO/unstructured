#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --ms-client-id "$MS_CLIENT_ID" \
    --ms-client-cred "$MS_CLIENT_CRED" \
    --ms-tenant "22175133-950a-4ca9-9fa9-c8d240fb8edc" \
    --ms-user-pname "test-ingest-admin@030rx.onmicrosoft.com" \
    --structured-output-dir onedrive-ingest-output \
    --download-dir files-ingest-download/onedrive \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --num-processes 2

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp onedrive-output/* test_unstructured_ingest/expected-structured-output/onedrive-output/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/onedrive-output onedrive-output ; then

    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
    echo
    echo "  export OVERWRITE_FIXTURES=true"
    echo
    echo "and then rerun this script."
    echo
    echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
    echo "to update fixtures for CI."
    echo
    exit 1

fi
