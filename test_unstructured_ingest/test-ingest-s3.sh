#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/s3-small-batch/ -type f -size +20k | wc -l)" -ne 3 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --s3-url s3://utic-dev-tech-fixtures/small-pdf-set/ \
    --s3-anonymous \
    --structured-output-dir s3-small-batch-output \
    --preserve-downloads \
    --reprocess

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp s3-small-batch-output/small-pdf-set/* test_unstructured_ingest/expected-structured-output/s3-small-batch/small-pdf-set/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/s3-small-batch s3-small-batch-output ; then
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
