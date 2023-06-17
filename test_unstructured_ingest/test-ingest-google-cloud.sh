#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/google-cloud-storage/ -type f -size +1 | wc -l)" -ne 1 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

if [ -z "$GCP_INGEST_SERVICE_KEY" ]; then
   echo "Skipping Google Drive ingest test because the GCP_INGEST_SERVICE_KEY env var is not set."
   exit 0
fi

# Create a temporary file
GCP_INGEST_SERVICE_KEY_FILE=$(mktemp)
cat "$GCP_INGEST_SERVICE_KEY" > "$GCP_INGEST_SERVICE_KEY_FILE"
# echo "$GCP_INGEST_SERVICE_KEY" > "$GCP_INGEST_SERVICE_KEY_FILE"


PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --remote-url gs://utic-test-ingest-fixtures/ \
    --structured-output-dir gcs-output \
    --gcs-token  "$GCP_INGEST_SERVICE_KEY_FILE" \
    --recursive \
    --preserve-downloads \
    --reprocess 

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp gcs-output* test_unstructured_ingest/expected-structured-output/google-cloud-storage

elif ! diff -ru test_unstructured_ingest/expected-structured-output/google-cloud-storage gcs-output ; then
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
    echo "to update fixtures for CI,"
    echo
    exit 1

fi
