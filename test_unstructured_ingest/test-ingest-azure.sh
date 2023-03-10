***REMOVED***!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --remote-url abfs://container1/ \
    --azure-account-name azureunstructured1 \
    --structured-output-dir azure-ingest-output \
    --num-processes 2

if [ "$(find 'azure-ingest-output' -type f -printf '.' | wc -c)" -ne 5 ]; then
    echo
    echo "5 files should have been created."
    exit 1
fi
