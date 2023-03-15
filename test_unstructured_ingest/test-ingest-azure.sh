#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --remote-url abfs://container1/ \
    --azure-account-name azureunstructured1 \
    --structured-output-dir azure-ingest-output \
    --num-processes 2

if ! diff -ru test_unstructured_ingest/expected-structured-output/azure-blob-storage azure-ingest-output ; then
    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite the fixtures with: "
    echo
    echo " cp azure-ingest-output/* test_unstructured_ingest/expected-structured-output/azure-blob-storage/"
    echo
    echo "after running this script."
    exit 1
fi
