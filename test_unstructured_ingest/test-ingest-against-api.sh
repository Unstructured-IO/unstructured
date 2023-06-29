#!/usr/bin/env bash

set -e

# TODO(crag): do not exit 0 but proceed with the test if an API key env var is defined
# shellcheck disable=SC2317
exit 0

#SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
#cd "$SCRIPT_DIR"/.. || exit 1
#
#PYTHONPATH=. ./unstructured/ingest/main.py \
#    --local-input-path example-docs \
#    --local-file-glob "*.pdf" \
#    --structured-output-dir api-ingest-output \
#    --partition-by-api \
#    --partition-strategy hi_res \
#    --verbose \
#    --reprocess
#
#set +e
#
#if [ "$(find 'api-ingest-output' -type f -printf '.' | wc -c)" != 8 ]; then
#   echo
#   echo "8 files should have been created."
#   exit 1
#fi
