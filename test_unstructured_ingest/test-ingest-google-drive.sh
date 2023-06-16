#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
   echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
   exit 0
fi

# Create a temporary file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
echo "$GCP_INGEST_SERVICE_KEY" > "$GCP_INGEST_SERVICE_KEY_FILE"

PYTHONPATH=. unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --drive-id 1OQZ66OHBE30rNsNa7dweGLfRmXvkT_jr \
    --drive-service-account-key "$GCP_INGEST_SERVICE_KEY_FILE" \
    --structured-output-dir google-drive-output \
    --download-dir files-ingest-download/google-drive \
    --partition-strategy hi_res \
    --preserve-downloads \
    --reprocess \
    --num-processes 2

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp google-drive-output/* test_unstructured_ingest/expected-structured-output/google-drive-output/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/google-drive-output google-drive-output ; then

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
