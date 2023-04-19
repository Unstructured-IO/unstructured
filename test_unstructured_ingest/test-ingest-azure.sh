#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --remote-url abfs://container1/ \
    --azure-account-name azureunstructured1 \
    --structured-output-dir azure-ingest-output \
    --reprocess \
    --num-processes 2

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp azure-ingest-output/* test_unstructured_ingest/expected-structured-output/azure-blob-storage/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/azure-blob-storage azure-ingest-output ; then

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
