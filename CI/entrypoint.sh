#!/usr/bin/env bash

cd /unstructured || exit
# shellcheck source=/dev/null
source .venv/bin/activate
./test_unstructured_ingest/test-ingest.sh
