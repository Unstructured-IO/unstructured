#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$(find test_unstructured_ingest/expected-structured-output/s3-small-batch/ -type f -size +20k | wc -l)" -ne 3 ]]; then
    echo "The test fixtures in test_unstructured_ingest/expected-structured-output/ look suspicious. At least one of the files is too small."
    echo "Did you overwrite test fixtures with bad outputs?"
    exit 1
fi

PYTHONPATH=. ./unstructured/ingest/main.py --s3-url s3://utic-dev-tech-fixtures/small-pdf-set/ --s3-anonymous --structured-output-dir s3-small-batch-output

if [[ "$(diff -r test_unstructured_ingest/expected-structured-output/s3-small-batch/ s3-small-batch-output/ | wc -l)" -ne 0 ]]; then
    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, copy the outputs from"
    echo "s3-small-batch-output/ to test_unstructured_ingest/expected-structured-output/s3-small-batch/ after running"
    echo
    echo "  PYTHONPATH=. python examples/ingest/s3-small-batch/main.py --structured-output-dir s3-small-batch-output"
    echo
    exit 1
fi
