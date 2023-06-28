#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
    --local-input-path example-docs/english-and-korean.png \
    --structured-output-dir parameterized-ingest-output \
    --partition-ocr-languages eng+kor \
    --partition-strategy ocr_only \
    --verbose \
    --reprocess

set +e

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp -r parameterized-ingest-output/ test_unstructured_ingest/expected-structured-output/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/parameterized-ingest-output parameterized-ingest-output ; then
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
