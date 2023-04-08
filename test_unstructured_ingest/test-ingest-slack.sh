***REMOVED***!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
        --slack-channel "${SLACK_CHANNEL}" \
        --slack-token "${SLACK_TOKEN}" \
        --download-dir slack-ingest-download \
        --structured-output-dir slack-ingest-output 

if [ "$(find 'slack-ingest-output' -type f -printf '.' | wc -c)" -ne 1 ]; then
    echo
    echo "1 files should have been created."
    exit 1
fi
