#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --ms-client-id "<Azure AD app client-id>" \
    --ms-client-cred "<Azure AD app client-secret>" \
    --ms-authority-url "<Authority URL, default is https://login.microsoftonline.com>" \
    --ms-tenant "<Azure AD tenant_id, default is 'common'>" \
    --ms-user-pname "<Azure AD principal name, in most cases is the email linked to the drive>" \
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
